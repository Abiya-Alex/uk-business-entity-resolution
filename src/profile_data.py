import csv
import json
import sys
from collections import Counter
from src.matching import name_key, postcode_key


def profile(path):
    count=0; missing: Counter[str]=Counter(); names: Counter[tuple[str,str]]=Counter(); ids: Counter[str]=Counter()
    with open(path,encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            count+=1
            for field in ('id','name','address','postcode'):
                if not row.get(field,'').strip(): missing[field]+=1
            names[(name_key(row['name']),postcode_key(row['postcode']))]+=1
            ids[row['id']]+=1
    return {'records':count,'missing':dict(missing),'duplicate_ids':sum(n-1 for n in ids.values() if n>1),'repeated_name_postcode':sum(n-1 for n in names.values() if n>1)}

if __name__=='__main__':
    print(json.dumps({p:profile(p) for p in sys.argv[1:]},indent=2))
