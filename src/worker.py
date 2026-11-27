import json
import logging
import time
from pydantic import ValidationError
from sqlalchemy import text
from src.db import engine, init_db
from src.matching import Record, CandidateIndex, score, decision, postcode_key
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
            conn.execute(text('INSERT INTO matches(fsa_id,company_id,name,postcode,score,status) VALUES (:f,:c,:n,:p,:s,:t) ON CONFLICT(fsa_id,company_id) DO NOTHING'), {'f':record.id,'c':candidate.id,'n':record.name,'p':postcode_key(record.postcode),'s':value,'t':status})


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    init_db()
    sqs = client()
    url = queue_url(sqs)
    while True:
        try:
            with engine.connect() as conn:
                index = CandidateIndex(Record(**dict(r)) for r in conn.execute(text('SELECT * FROM companies')).mappings())
            for msg in sqs.receive_message(QueueUrl=url, MaxNumberOfMessages=10, WaitTimeSeconds=10).get('Messages',[]):
                try:
                    job = json.loads(msg['Body'])
                    process(job['job_id'], job['record'], index)
                    sqs.delete_message(QueueUrl=url, ReceiptHandle=msg['ReceiptHandle'])
                    log.info(json.dumps({"event":"job_processed","job_id":job["job_id"]}))
                except Exception:
                    log.exception('processing failed; message retained for retry')
        except Exception:
            log.exception('poll failed')
            time.sleep(3)

if __name__ == '__main__':
    main()
