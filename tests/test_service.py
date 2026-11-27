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
