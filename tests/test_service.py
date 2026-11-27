import pytest
from sqlalchemy import create_engine,text
from fastapi.testclient import TestClient
from src import db, api, worker
from src.matching import CandidateIndex, Record

@pytest.fixture
def database(tmp_path,monkeypatch):
    eng=create_engine('sqlite:///'+str(tmp_path/'test.db'))
    for module in (db,api,worker): monkeypatch.setattr(module,'engine',eng)
    db.init_db()
    yield eng
    eng.dispose()


def test_process_retry_search(database):
    index=CandidateIndex([Record(id='C1',name='ABC Ltd',address='25 High Street',postcode='TN9 1AB')])
    payload=dict(id='F1',name='ABC Limited',address='25 High St',postcode='TN9 1AB')
    worker.process('job1',payload,index)
    worker.process('job1',payload,index)
    with database.connect() as conn:
        assert conn.execute(text('SELECT count(*) FROM matches')).scalar()==1
    with TestClient(api.app) as client:
        assert client.get('/health').status_code==200
        assert len(client.get('/business',params={'name':'ABC','postcode':'TN9 1AB'}).json())==1
        assert client.get('/business').status_code==422
        assert client.get('/metrics').status_code==200


def test_quarantine(database):
    worker.process('bad',{},CandidateIndex([]))
    with database.connect() as conn:
        assert conn.execute(text('SELECT count(*) FROM quarantine')).scalar()==1


def test_review(database):
    with database.begin() as conn:
        conn.execute(text("INSERT INTO matches VALUES ('F','C','name','TN91AB',75,'review')"))
    with TestClient(api.app) as client:
        assert len(client.get('/review').json())==1
        assert client.post('/review/F/C',params={'status':'approved'}).status_code==200
        assert client.post('/review/F/C',params={'status':'rejected'}).status_code==404


def test_index_refresh_after_receive(database):
    # Simulate a company import committing while the queue receive is blocked.
    import json
    cache = worker.IndexCache()
    assert cache.get().candidates(Record(id='F1', name='ABC Foods Ltd', postcode='TN9 1AB')) == []
    class Queue:
        deleted = False
        def receive_message(self, **kwargs):
            with database.begin() as conn:
                conn.execute(text("INSERT INTO companies VALUES ('C1','ABC Foods Limited','25 High Street','TN9 1AB')"))
                conn.execute(text('UPDATE company_revision SET revision=revision+1 WHERE id=1'))
            payload = dict(id='F1', name='ABC Foods Ltd', address='25 High St.', postcode='TN9 1AB')
            return {'Messages': [{'Body': json.dumps({'job_id':'abc-fresh','record':payload}), 'ReceiptHandle':'abc'}]}
        def delete_message(self, **kwargs):
            self.deleted = True
    sqs = Queue()
    assert worker.poll_once(sqs, 'local', cache) == 1
    assert sqs.deleted
    assert cache.builds == 2
    cached = cache.get()
    assert cache.get() is cached
    assert cache.builds == 2
    with database.connect() as conn:
        assert conn.execute(text("SELECT score FROM matches WHERE fsa_id='F1' AND company_id='C1'")).scalar_one() == 100


def test_worker_retains_invalid_message(database):
    class Queue:
        def receive_message(self, **kwargs):
            return {'Messages': [{'Body':'not JSON','ReceiptHandle':'bad'}]}
        def delete_message(self, **kwargs):
            raise AssertionError('Malformed job must not be acknowledged')
    assert worker.poll_once(Queue(), 'local', worker.IndexCache()) == 0


def test_worker_empty_poll(database):
    class Queue:
        def receive_message(self, **kwargs):
            return {}
    cache = worker.IndexCache()
    assert worker.poll_once(Queue(), 'local', cache) == 0
    assert cache.builds == 0
