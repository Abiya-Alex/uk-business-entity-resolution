"""Evaluate labelled candidate pairs; include missed blocking candidates as negatives."""
import argparse
import csv
import json
from src.matching import Record, score, decision, keys


def evaluate(rows):
    tp=fp=fn=tn=review=0
    for row in rows:
        a=Record(id='a',name=row['a_name'],address=row['a_address'],postcode=row['a_postcode'])
        b=Record(id='b',name=row['b_name'],address=row['b_address'],postcode=row['b_postcode'])
        truth=row['label'].strip()
        if truth not in {'0','1'}:
            raise ValueError('Every label must be 0 or 1')
        result=decision(score(a,b)) if keys(a)&keys(b) else 'no_match'
        pred=result=='auto_match'
        review+=result=='review'
        tp+=pred and truth=='1'; fp+=pred and truth=='0'
        fn+=not pred and truth=='1'; tn+=not pred and truth=='0'
    p=tp/(tp+fp) if tp+fp else 0
    r=tp/(tp+fn) if tp+fn else 0
    return dict(tp=tp,fp=fp,fn=fn,tn=tn,review=review,precision=p,recall=r,f1=2*p*r/(p+r) if p+r else 0)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('labels'); args=parser.parse_args()
    with open(args.labels,encoding='utf-8-sig',newline='') as f:
        print(json.dumps(evaluate(csv.DictReader(f)),indent=2))
