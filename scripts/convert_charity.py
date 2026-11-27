"""Convert confirmed Charity Commission TSV schema; keep reference links separate."""
import argparse
import csv
import hashlib
import json
import random
import re
from collections import Counter
from pathlib import Path
from src.matching import Record, name_key

FIELDS = ['id', 'name', 'address', 'postcode']


def company_number(value):
    value = re.sub(r'\s+', '', value.upper())
    if re.fullmatch(r'[0-9]{1,8}', value) and int(value):
        return value.zfill(8)
    if re.fullmatch(r'[A-Z]{2}[0-9]{1,6}', value) and int(value[2:]):
        return value[:2] + value[2:].zfill(6)
    return value if re.fullmatch(r'[A-Z0-9]{8}', value) and any(c.isdigit() and c != '0' for c in value) else ''


def write_csv(path, fields, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def convert(source, out, limit, seed=42):
    counts = Counter()
    statuses = Counter()
    dates = Counter()
    eligible = {}
    csv.field_size_limit(10_000_000)
    with open(source, 'rb') as raw:
        bom=raw.read(4)
    encoding='utf-16' if bom.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'
    with open(source, encoding=encoding, newline='') as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        required = {'organisation_number','charity_name','charity_registration_status','charity_company_registration_number','charity_contact_postcode','date_of_extract'} | {f'charity_contact_address{i}' for i in range(1,6)}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('Required charity columns missing')
        for row in reader:
            counts['rows'] += 1
            status = (row.get('charity_registration_status') or '').strip().casefold()
            statuses[status] += 1
            dates[(row.get('date_of_extract') or '').strip()] += 1
            if status != 'registered':
                continue
            counts['registered'] += 1
            raw = (row.get('charity_company_registration_number') or '').strip()
            if not raw:
                continue
            counts['registered_nonblank_company_number'] += 1
            number = company_number(raw)
            if not number:
                counts['invalid_number_format'] += 1
                continue
            identity = (row.get('organisation_number') or '').strip()
            name = (row.get('charity_name') or '').strip()
            address = ', '.join(v for i in range(1,6) if (v := (row.get(f'charity_contact_address{i}') or '').strip()))
            postcode = (row.get('charity_contact_postcode') or '').strip()
            if not identity or not name_key(name) or len(name)>500 or len(address)>1000 or len(postcode)>20:
                counts['invalid_record'] += 1
                continue
            counts['usable_rows'] += 1
            counts['missing_address'] += not bool(address)
            counts['missing_postcode'] += not bool(postcode)
            rid = 'charity:' + hashlib.sha256(identity.encode()).hexdigest()[:24]
            rec = Record(id=rid,name=name,address=address,postcode=postcode).model_dump()
            # One deterministic representative per company, preventing group leakage.
            if number not in eligible or rid < eligible[number]['id']:
                eligible[number] = rec
    if not eligible:
        raise ValueError(f'No eligible companies: {dict(statuses)}')
    ids = sorted(eligible)
    random.Random(seed).shuffle(ids)
    selected = ids[:limit]
    rows = [eligible[n] for n in selected]
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Conflicting company numbers for the same charity identifier; inspect source')
    out = Path(out)
    write_csv(out/'charities.csv', FIELDS, rows)
    write_csv(out/'truth.csv', ['charity_id','company_number'], [{'charity_id':eligible[n]['id'],'company_number':n} for n in selected])
    profile = dict(counts, unique_eligible_companies=len(eligible), selected=len(selected), registration_statuses=dict(statuses), extract_dates=dict(dates), seed=seed, selection='one deterministic charity per company; seeded sample')
    (out/'profile.json').write_text(json.dumps(profile,indent=2),encoding='utf-8')
    return profile


def main():
    p=argparse.ArgumentParser(); p.add_argument('source'); p.add_argument('out'); p.add_argument('--limit',type=int,default=500); a=p.parse_args()
    if a.limit < 1: p.error('positive limit required')
    print(json.dumps(convert(a.source,a.out,a.limit),indent=2))

if __name__=='__main__': main()
