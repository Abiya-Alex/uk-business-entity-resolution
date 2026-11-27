"""Import canonical CSV files; commit company changes before enqueueing jobs."""
import argparse
import csv
import hashlib
import json
from typing import Any
from pydantic import ValidationError
from sqlalchemy import text
from src.db import engine, init_db
from src.matching import Record, name_key
from src.queue import client, queue_url


def import_companies(path: str) -> tuple[int, int]:
    accepted = rejected = 0
    with open(path, encoding='utf-8-sig', newline='') as stream, engine.begin() as conn:
        changed = False
        for row in csv.DictReader(stream):
            try:
                if None in row:
                    raise ValueError('Unexpected extra CSV fields')
                record = Record.model_validate(row)
                if not record.id.strip() or not name_key(record.name):
                    raise ValueError('Missing usable company ID or name')
            except (ValidationError, ValueError) as exc:
                # Avoid storing raw field values or leaking them in error messages.
                reason = (json.dumps(exc.errors(include_input=False, include_context=False, include_url=False), default=str)
                          if isinstance(exc, ValidationError) else str(exc))
                digest = hashlib.sha256(json.dumps(list(row.items()), default=str).encode()).hexdigest()
                conn.execute(text('INSERT INTO quarantine(job_id,reason) VALUES (:id,:reason) ON CONFLICT(job_id) DO NOTHING'),
                             {'id': 'company:' + digest, 'reason': 'company row: ' + reason})
                rejected += 1
                continue
            result = conn.execute(text('INSERT INTO companies(id,name,address,postcode) VALUES (:id,:name,:address,:postcode) ON CONFLICT(id) DO UPDATE SET name=excluded.name,address=excluded.address,postcode=excluded.postcode WHERE companies.name != excluded.name OR companies.address != excluded.address OR companies.postcode != excluded.postcode'),record.model_dump())
            changed = changed or bool(result.rowcount)
            accepted += 1
        if changed:
            conn.execute(text('UPDATE company_revision SET revision=revision+1 WHERE id=1'))
    return accepted, rejected


def enqueue_fsa(path: str, sqs: Any, url: str) -> int:
    count = 0
    with open(path, encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            # Preserve job IDs for valid rows from the previous version.
            if None in row:
                digest = hashlib.sha256(json.dumps(list(row.items()), default=str).encode()).hexdigest()
                row = {'invalid_csv_row': digest}
            canonical = json.dumps(row, sort_keys=True)
            job_id = hashlib.sha256(canonical.encode()).hexdigest()
            sqs.send_message(QueueUrl=url, MessageBody=json.dumps({'job_id':job_id,'record':row}))
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('companies')
    parser.add_argument('fsa')
    args = parser.parse_args()
    init_db()
    accepted, rejected = import_companies(args.companies)
    sqs = client()
    queued = enqueue_fsa(args.fsa, sqs, queue_url(sqs))
    print(f'Companies accepted: {accepted}; rejected: {rejected}; FSA jobs queued: {queued}')


if __name__ == '__main__':
    main()
