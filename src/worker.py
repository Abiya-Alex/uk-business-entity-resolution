import json
import logging
import time
from typing import Any
from pydantic import ValidationError
from sqlalchemy import text
from src.db import engine, init_db
from src.matching import Record, CandidateIndex, score, decision, postcode_key, name_key
from src.queue import client, queue_url

log = logging.getLogger(__name__)


def process(job_id: str, payload: dict, index: CandidateIndex) -> None:
    with engine.begin() as conn:
        result = conn.execute(text('INSERT INTO processed(job_id) VALUES (:id) ON CONFLICT DO NOTHING'), {'id':job_id})
        if result.rowcount == 0:
            return
        try:
            record = Record.model_validate(payload)
        except ValidationError as exc:
            conn.execute(text('INSERT INTO quarantine(job_id,reason) VALUES (:id,:reason)'), {'id':job_id,'reason':str(exc)})
            return
        for candidate in index.candidates(record):
            value = score(record,candidate)
            status = decision(value)
            if status == 'no_match':
                continue
            conn.execute(text('INSERT INTO matches(fsa_id,company_id,name,postcode,score,status,normalized_name) VALUES (:f,:c,:n,:p,:s,:t,:nn) ON CONFLICT(fsa_id,company_id) DO NOTHING'), {'f':record.id,'c':candidate.id,'n':record.name,'p':postcode_key(record.postcode),'s':value,'t':status,'nn':name_key(record.name)})


class IndexCache:
    """Refresh only after a committed company import changes the revision."""

    def __init__(self) -> None:
        self.revision: int | None = None
        self.index = CandidateIndex([])
        self.builds = 0

    def get(self) -> CandidateIndex:
        # Check after receiving messages: ingestion commits before publishing.
        # The double read prevents caching a mixed snapshot during an import.
        with engine.connect() as conn:
            for _ in range(3):
                revision = int(conn.execute(text('SELECT revision FROM company_revision WHERE id=1')).scalar_one())
                if revision == self.revision:
                    return self.index
                records = [Record(**dict(r)) for r in conn.execute(text('SELECT * FROM companies')).mappings()]
                after = int(conn.execute(text('SELECT revision FROM company_revision WHERE id=1')).scalar_one())
                if revision == after:
                    self.index = CandidateIndex(records)
                    self.revision = revision
                    self.builds += 1
                    return self.index
        raise RuntimeError('Company snapshot changed during index refresh; retry batch')


def poll_once(sqs: Any, url: str, cache: IndexCache) -> int:
    messages = sqs.receive_message(QueueUrl=url, MaxNumberOfMessages=10, WaitTimeSeconds=10).get('Messages', [])
    if not messages:
        return 0
    index = cache.get()
    completed = 0
    for msg in messages:
        try:
            job = json.loads(msg['Body'])
            process(job['job_id'], job['record'], index)
            sqs.delete_message(QueueUrl=url, ReceiptHandle=msg['ReceiptHandle'])
            log.info(json.dumps({"event":"job_processed","job_id":job["job_id"]}))
            completed += 1
        except Exception:
            log.exception('processing failed; message retained for retry')
    return completed


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    init_db()
    sqs = client()
    url = queue_url(sqs)
    cache = IndexCache()
    while True:
        try:
            poll_once(sqs, url, cache)
        except Exception:
            log.exception('poll failed')
            time.sleep(3)

if __name__ == '__main__':
    main()
