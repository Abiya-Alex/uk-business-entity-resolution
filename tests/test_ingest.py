import json
import sys
from sqlalchemy import create_engine, text
from src import db, ingest, worker


def test_ingest_quarantines_bad_rows_and_updates_revision(tmp_path, monkeypatch):
    eng = create_engine('sqlite:///' + str(tmp_path/'ingestion.db'))
    for module in (db, ingest, worker):
        monkeypatch.setattr(module, 'engine', eng)
    db.init_db()
    companies = tmp_path/'companies.csv'
    companies.write_text('id,name,address,postcode\nC1,ABC Foods Ltd,25 High Street,TN9 1AB\n,Invalid,,\nC2,   ,,\nC3,Green Cafe Ltd,8 Market Road,TN9 2CD\n')
    premises = tmp_path/'fsa.csv'
    premises.write_text('id,name,address,postcode\nF1,ABC Foods Ltd,25 High St.,TN9 1AB\n')
    class Queue:
        def __init__(self):
            self.messages = []
        def get_queue_url(self, **kwargs):
            return {'QueueUrl':'local'}
        def send_message(self, **kwargs):
            self.messages.append(json.loads(kwargs['MessageBody']))
    sqs = Queue()
    monkeypatch.setattr(ingest, 'client', lambda: sqs)
    monkeypatch.setattr(sys, 'argv', ['ingest', str(companies), str(premises)])
    ingest.main()
    cache = worker.IndexCache()
    index = cache.get()
    worker.process(sqs.messages[0]['job_id'], sqs.messages[0]['record'], index)
    with eng.connect() as conn:
        assert conn.execute(text('SELECT COUNT(*) FROM companies')).scalar_one() == 2
        assert conn.execute(text('SELECT COUNT(*) FROM quarantine')).scalar_one() == 2
        assert conn.execute(text('SELECT revision FROM company_revision')).scalar_one() == 1
        assert conn.execute(text('SELECT COUNT(*) FROM matches')).scalar_one() == 1
    assert ingest.import_companies(str(companies)) == (2, 2)
    assert cache.get() is index
    companies.write_text('id,name,address,postcode\nC1,ABC Updated Ltd,25 High Street,TN9 1AB\n')
    assert ingest.import_companies(str(companies)) == (1, 0)
    assert cache.get() is not index
    assert cache.builds == 2
    with eng.connect() as conn:
        assert conn.execute(text('SELECT revision FROM company_revision')).scalar_one() == 2
        assert conn.execute(text('SELECT COUNT(*) FROM quarantine')).scalar_one() == 2
    eng.dispose()


def test_ingest_extra_columns_are_quarantined(tmp_path, monkeypatch):
    eng = create_engine('sqlite:///' + str(tmp_path/'ingestion.db'))
    for module in (db, ingest):
        monkeypatch.setattr(module, 'engine', eng)
    db.init_db()
    source = tmp_path/'companies.csv'
    source.write_text('id,name,address,postcode\nC1,ABC Ltd,25 High Street,TN9 1AB,extra\n')
    assert ingest.import_companies(str(source)) == (0, 1)
    eng.dispose()
