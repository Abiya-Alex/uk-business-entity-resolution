"""Fetch minimal company fields, cache atomically in SQLite, and resume."""
import argparse
import base64
import csv
import json
import os
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from scripts.convert_charity import FIELDS, company_number, write_csv
from src.matching import postcode_key

BASE = 'https://api.company-information.service.gov.uk'


class Client:
    def __init__(self, key, cache):
        self.auth = 'Basic ' + base64.b64encode((key+':').encode()).decode()
        self.db = sqlite3.connect(cache)
        self.db.execute('CREATE TABLE IF NOT EXISTS responses (path TEXT PRIMARY KEY, body TEXT, retrieved TEXT)')
        self.last = 0.0
        self.calls = 0

    def get(self,path):
        saved=self.db.execute('SELECT body FROM responses WHERE path=?',(path,)).fetchone()
        if saved: return json.loads(saved[0])
        for attempt in range(6):
            time.sleep(max(0, 0.75-(time.monotonic()-self.last)))
            self.last=time.monotonic(); self.calls+=1
            try:
                req=urllib.request.Request(BASE+path,headers={'Authorization':self.auth,'Accept':'application/json'})
                with urllib.request.urlopen(req,timeout=30) as response:
                    raw=json.load(response)
                if path.startswith('/company/'):
                    result=canonical(raw)
                else:
                    result=[canonical(x) for x in raw.get('items',[]) ]
                break
            except urllib.error.HTTPError as exc:
                if exc.code==404:
                    result=None; break
                if exc.code not in (429,500,502,503,504):
                    raise RuntimeError(f'API HTTP {exc.code}; check credentials or request parameters') from None
                if attempt==5: raise RuntimeError('API retry budget exhausted; rerun to resume') from None
                retry=exc.headers.get('Retry-After','')
                time.sleep(max(305 if exc.code==429 else 2**attempt, int(retry) if retry.isdigit() else 0))
            except (urllib.error.URLError,TimeoutError):
                if attempt==5: raise RuntimeError('Network retry budget exhausted; rerun to resume') from None
                time.sleep(2**attempt)
        self.db.execute('INSERT INTO responses VALUES (?,?,?)',(path,json.dumps(result),datetime.now(timezone.utc).isoformat()))
        self.db.commit()
        return result


def canonical(raw):
    addr=raw.get('registered_office_address') or raw.get('address') or {}
    number=company_number(str(raw.get('company_number') or ''))
    name=str(raw.get('company_name') or raw.get('title') or '').strip()
    address=', '.join(str(addr[k]).strip() for k in ('premises','address_line_1','address_line_2','locality','region','country') if addr.get(k))
    postcode=str(addr.get('postal_code') or '').strip()
    if not number or not name or len(name)>500 or len(address)>1000 or len(postcode)>20: return None
    return dict(id=number,name=name,address=address,postcode=postcode)


def fetch(directory,cache,key,distractor_locations):
    directory=Path(directory)
    with (directory/'truth.csv').open(encoding='utf-8',newline='') as f:
        truth=list(csv.DictReader(f))
    client=Client(key,cache)
    companies={}; failed=[]
    numbers=sorted({r['company_number'] for r in truth})
    for i,n in enumerate(numbers,1):
        rec=client.get('/company/'+urllib.parse.quote(n,safe=''))
        if rec and rec['id']==n: companies[n]=rec
        else: failed.append(n)
        if i%50==0: print(f'Linked lookups: {i}/{len(numbers)}; network requests: {client.calls}',flush=True)
    linked=len(companies)
    with (directory/'charities.csv').open(encoding='utf-8',newline='') as f:
        locations=sorted({postcode_key(r['postcode']) for r in csv.DictReader(f) if len(postcode_key(r['postcode']))>3})
    # Seeded postcode sample; location search is not a radius search.
    import random
    random.Random(42).shuffle(locations)
    searched=locations[:distractor_locations]
    for i,loc in enumerate(searched,1):
        formatted=loc[:-3]+' '+loc[-3:]
        path='/advanced-search/companies?'+urllib.parse.urlencode({'location':formatted,'size':10})
        for rec in client.get(path) or []:
            if rec and rec['id'] not in numbers and postcode_key(rec['postcode'])==loc:
                companies.setdefault(rec['id'],rec)
        if i%25==0: print(f'Postcode searches: {i}/{len(searched)}',flush=True)
    write_csv(directory/'companies.csv',FIELDS,sorted(companies.values(),key=lambda r:r['id']))
    write_csv(directory/'retrieval_failures.csv',['company_number'],[{'company_number':n} for n in failed])
    dates=client.db.execute('SELECT min(retrieved),max(retrieved) FROM responses').fetchone()
    report={'requested_linked':len(numbers),'retrieved_linked':linked,'unavailable_or_invalid':len(failed),'distractors':len(companies)-linked,'candidate_pool':len(companies),'candidate_missing_address':sum(not r['address'] for r in companies.values()),'candidate_missing_postcode':sum(not r['postcode'] for r in companies.values()),'postcode_searches':len(searched),'network_requests_this_run':client.calls,'cache_retrieval_window_utc':dates}
    client.db.close()
    (directory/'fetch-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser(); p.add_argument('directory'); p.add_argument('--cache',required=True); p.add_argument('--distractor-locations',type=int,default=100); a=p.parse_args()
    key=os.getenv('CH_API_KEY');
    if not key: p.error('CH_API_KEY is not configured')
    print(json.dumps(fetch(a.directory,a.cache,key,a.distractor_locations),indent=2))

if __name__=='__main__': main()
