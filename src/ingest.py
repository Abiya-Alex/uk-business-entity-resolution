"""Import canonical CSV files; run company import before enqueueing FSA jobs."""
import argparse
import csv
import hashlib
import json
from sqlalchemy import text
from src.db import engine, init_db
from src.matching import Record
from src.queue import client, queue_url


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('companies')
    parser.add_argument('fsa')
    args=parser.parse_args()
    init_db()
    with open(args.companies,encoding='utf-8-sig',newline='') as stream, engine.begin() as conn:
        changed = False
        for row in csv.DictReader(stream):
            record=Record.model_validate(row)
            result = conn.execute(text('INSERT INTO companies(id,name,address,postcode) VALUES (:id,:name,:address,:postcode) ON CONFLICT(id) DO UPDATE SET name=excluded.name,address=excluded.address,postcode=excluded.postcode WHERE companies.name != excluded.name OR companies.address != excluded.address OR companies.postcode != excluded.postcode'),record.model_dump())
            changed = changed or bool(result.rowcount)
        if changed:
            conn.execute(text('UPDATE company_revision SET revision=revision+1 WHERE id=1'))
    sqs=client()
    url=queue_url(sqs)
    with open(args.fsa,encoding='utf-8-sig',newline='') as stream:
        for row in csv.DictReader(stream):
            canonical=json.dumps(row,sort_keys=True)
            job_id=hashlib.sha256(canonical.encode()).hexdigest()
            sqs.send_message(QueueUrl=url,MessageBody=json.dumps({'job_id':job_id,'record':row}))

if __name__=='__main__':
    main()
