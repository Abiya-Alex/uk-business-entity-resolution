"""Evaluate labelled candidate pairs; include missed blocking candidates as negatives."""
import argparse
import csv
import json
from src.matching import CandidateIndex, Record, score, decision, keys


def evaluate(rows, company_index: CandidateIndex | None = None):
    tp=fp=fn=tn=review=0
    for row in rows:
        a=Record(id=row.get('a_id') or 'a',name=row['a_name'],address=row['a_address'],postcode=row['a_postcode'])
        b=Record(id=row.get('b_id') or 'b',name=row['b_name'],address=row['b_address'],postcode=row['b_postcode'])
        truth=row['label'].strip()
        if truth not in {'0','1'}:
            raise ValueError('Every label must be 0 or 1')
        if company_index is not None:
            if not row.get('b_id'):
                raise ValueError('b_id is required when evaluating with the company corpus')
            eligible = any(candidate.id == b.id for candidate in company_index.candidates(a))
        else:
            eligible = bool(keys(a) & keys(b))
        result=decision(score(a,b)) if eligible else 'no_match'
        pred=result=='auto_match'
        review+=result=='review'
        tp+=pred and truth=='1'; fp+=pred and truth=='0'
        fn+=not pred and truth=='1'; tn+=not pred and truth=='0'
    p=tp/(tp+fp) if tp+fp else 0
    r=tp/(tp+fn) if tp+fn else 0
    return dict(tp=tp,fp=fp,fn=fn,tn=tn,review=review,precision=p,recall=r,f1=2*p*r/(p+r) if p+r else 0)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('labels'); parser.add_argument('--companies', help='Canonical company CSV for full candidate filtering'); args=parser.parse_args()
    index = None
    if args.companies:
        from src.sample_pairs import records
        index = CandidateIndex(records(args.companies))
    with open(args.labels,encoding='utf-8-sig',newline='') as f:
        print(json.dumps(evaluate(csv.DictReader(f), index),indent=2))
