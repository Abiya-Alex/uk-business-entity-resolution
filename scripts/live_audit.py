"""Run inside API container; emit aggregate snapshot/queue state only."""
import json
from sqlalchemy import text
from src.db import engine
from src.queue import client,queue_url

with engine.connect() as conn:
    counts={t:conn.execute(text('SELECT count(*) FROM '+t)).scalar_one() for t in ('companies','processed','matches','quarantine')}
    counts['auto_matches']=conn.execute(text("SELECT count(*) FROM matches WHERE status='auto_match'")).scalar_one()
    counts['review_matches']=conn.execute(text("SELECT count(*) FROM matches WHERE status='review'")).scalar_one()
    counts['distinct_auto_query_ids']=conn.execute(text("SELECT count(DISTINCT fsa_id) FROM matches WHERE status='auto_match'")).scalar_one()
sqs=client(); keys=['ApproximateNumberOfMessages','ApproximateNumberOfMessagesNotVisible','ApproximateNumberOfMessagesDelayed']
for name,url in [('jobs',queue_url(sqs)),('dead',sqs.get_queue_url(QueueName='dead')['QueueUrl'])]:
    counts[name]=sqs.get_queue_attributes(QueueUrl=url,AttributeNames=keys)['Attributes']
print(json.dumps(counts,indent=2))
