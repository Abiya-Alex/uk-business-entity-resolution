"""Convert downloaded Companies House CSV and FSA JSON into canonical regional CSVs."""

from collections.abc import Iterator
from typing import Any
import argparse
import csv
import json
from src.matching import postcode_key


def convert(source: str, target: str, kind: str, areas: list[str]) -> int:
    count = 0
    with open(source, encoding='utf-8-sig', newline='') as inp, open(target, 'w', encoding='utf-8', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=['id','name','address','postcode'])
        writer.writeheader()
        rows: Iterator[dict[str, Any]]
        if kind == 'companies':
            rows = ({k.strip():v for k,v in row.items()} for row in csv.DictReader(inp))
        else:
            payload = json.load(inp)
            rows = iter(payload if isinstance(payload,list) else payload['establishments'])
        for row in rows:
            if kind == 'companies':
                item = {'id':row.get('CompanyNumber',''),'name':row.get('CompanyName',''),'address':', '.join(str(row.get('RegAddress.'+k) or '') for k in ['AddressLine1','AddressLine2','PostTown'] if row.get('RegAddress.'+k)),'postcode':row.get('RegAddress.PostCode','')}
            else:
                item = {'id':str(row.get('FHRSID','')),'name':row.get('BusinessName',''),'address':', '.join(str(row[k]) for k in ['AddressLine1','AddressLine2','AddressLine3','AddressLine4'] if row.get(k)),'postcode':row.get('PostCode','')}
            postcode = postcode_key(str(item['postcode'] or ''))
            district = postcode[:-3]
            if any(district.startswith(a) and (len(district)==len(a) or district[len(a)].isdigit()) for a in areas) and item['id'] and item['name']:
                writer.writerow(item)
                count += 1
    return count

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('kind',choices=['companies','fsa']); parser.add_argument('source'); parser.add_argument('target'); parser.add_argument('--areas',nargs='+',default=['TN','ME']); args=parser.parse_args()
    print(convert(args.source,args.target,args.kind,[a.upper() for a in args.areas]))
