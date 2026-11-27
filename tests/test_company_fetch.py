import io
import json
from scripts import fetch_companies as fc


def test_canonical_and_persistent_cache(tmp_path,monkeypatch):
    payload={'company_number':'00000123','company_name':'Example Ltd','registered_office_address':{'address_line_1':'25 High Street','postal_code':'TN9 1AB'},'irrelevant':'not retained'}
    calls=[]
    def request(req,timeout):
        calls.append(req.full_url)
        return io.BytesIO(json.dumps(payload).encode())
    monkeypatch.setattr(fc.urllib.request,'urlopen',request)
    cache=tmp_path/'cache.db'; client=fc.Client('dummy',cache)
    result=client.get('/company/00000123'); client.db.close()
    assert result==dict(id='00000123',name='Example Ltd',address='25 High Street',postcode='TN9 1AB')
    client=fc.Client('dummy',cache)
    assert client.get('/company/00000123')==result
    assert len(calls)==1
    client.db.close()
