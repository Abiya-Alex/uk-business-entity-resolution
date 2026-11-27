"""Requeue the fictional ABC Foods fixture without deleting existing jobs."""
import csv
import hashlib
import json
from sqlalchemy import text
from src.db import engine
from src.queue import client, queue_url

expected = {'id':'F1', 'name':'ABC Foods Ltd', 'address':'25 High St.', 'postcode':'TN9 1AB'}
with open('data/fsa_demo.csv', encoding='utf-8-sig', newline='') as stream:
    rows = list(csv.DictReader(stream))
if expected not in rows:
    raise SystemExit('Demo fixture differs; nothing queued.')
with engine.connect() as conn:
    found = conn.execute(text("SELECT id,name,address,postcode FROM companies WHERE id='C1'")).mappings().first()
    if not found or dict(found) != {'id':'C1','name':'ABC Foods Limited','address':'25 High Street','postcode':'TN9 1AB'}:
        raise SystemExit('Expected demo company not found; nothing queued.')
    if conn.execute(text("SELECT COUNT(*) FROM matches WHERE fsa_id='F1' AND company_id='C1'")).scalar_one():
        raise SystemExit('Demo match already exists; nothing queued.')
job_id = hashlib.sha256(('phase-b-demo-replay:'+json.dumps(expected,sort_keys=True)).encode()).hexdigest()
sqs = client()
sqs.send_message(QueueUrl=queue_url(sqs), MessageBody=json.dumps({'job_id':job_id,'record':expected}))
print('Queued fictional F1 replay:', job_id)
