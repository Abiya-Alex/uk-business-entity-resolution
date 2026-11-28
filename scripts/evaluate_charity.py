"""Controlled-corpus, ID-hidden evaluation with separate tuning and holdout."""
import argparse
import csv
import hashlib
import json
import random
from pathlib import Path
from time import perf_counter
from rapidfuzz import fuzz
from src.matching import Record, CandidateIndex, name_key, address_key, postcode_key, score
from scripts.convert_charity import write_csv


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))


def fingerprint(directory):
    return {f: hashlib.sha256((directory/f).read_bytes()).hexdigest() for f in ('charities.csv','companies.csv','truth.csv')}


def features(r):
    return name_key(r.name),address_key(r.address),postcode_key(r.postcode)


def fast_score(a,b):
    n1,a1,p1=a; n2,a2,p2=b
    return round(.55*(fuzz.ratio(n1,n2) if n1 and n2 else 0)+.30*(fuzz.ratio(a1,a2) if a1 and a2 else 0)+15*bool(p1 and p1==p2),2)


def load(directory):
    queries=[Record.model_validate(r) for r in read_csv(directory/'charities.csv')]
    companies=[Record.model_validate(r) for r in read_csv(directory/'companies.csv')]
    truth={r['charity_id']:r['company_number'] for r in read_csv(directory/'truth.csv')}
    if len(queries)!=len(truth) or len(set(truth.values()))!=len(truth) or set(truth)!=set(r.id for r in queries):
        raise ValueError('Require one query per unique known company and exact truth coverage')
    if len(set(c.id for c in companies))!=len(companies): raise ValueError('Duplicate candidate ID')
    if len(queries)<10 or not companies: raise ValueError('Insufficient records for evaluation')
    # Split before looking at outcomes, keeping retrieval failures in denominators.
    # Converter orders the full sample so the pilot is its first 500 rows.
    pilot = queries[:500] if len(queries) > 1000 else []
    remaining = queries[len(pilot):]
    remaining.sort(key=lambda r:r.id); random.Random(42).shuffle(remaining)
    cut=int(len(queries)*.6)-len(pilot)
    return pilot+remaining[:cut],remaining[cut:],companies,truth


def counts(pred, target, pool):
    tp=int(target in pred); fp=len(pred)-tp; fn=1-tp
    # TN deliberately not reported: a missing positive may be outside the pool.
    return tp,fp,fn,int(target in pool)


def metrics(rows):
    tp,fp,fn,available=map(sum,zip(*rows))
    p=tp/(tp+fp) if tp+fp else 0.; r=tp/(tp+fn) if tp+fn else 0.
    return {'tp':tp,'fp':fp,'fn':fn,'precision':p,'recall':r,'f1':2*p*r/(p+r) if p+r else 0.,'reference_available':available,'recall_given_retrieval':tp/available if available else None}


def interval(rows):
    rng=random.Random(73); samples={k:[] for k in ('precision','recall','f1')}
    for _ in range(1000):
        m=metrics(rng.choices(rows,k=len(rows)))
        for k in samples: samples[k].append(m[k])
    return {k:[sorted(v)[24],sorted(v)[974]] for k,v in samples.items()}


def blocked(queries,companies,truth,thresholds):
    start=perf_counter(); index=CandidateIndex(companies)
    build=perf_counter()-start
    pool={c.id for c in companies}; results={t:[] for t in thresholds}; errors={t:[] for t in thresholds}
    comparisons=hits=reviews=0
    start=perf_counter()
    for q in queries:
        target=truth[q.id]; candidates=index.candidates(q); comparisons+=len(candidates)
        scored=[(c.id,score(q,c)) for c in candidates]
        hits+=any(cid==target for cid,_ in scored)
        reviews+=sum(65<=v<90 for _,v in scored)
        for t in thresholds:
            pred={cid for cid,v in scored if v>=t}; row=counts(pred,target,pool); results[t].append(row)
            if row[1] or row[2]:
                reason='retrieval_missing' if target not in pool else 'blocking_miss' if not any(cid==target for cid,_ in scored) else 'below_threshold' if target not in pred else 'extra_auto_matches'
                errors[t].append({'charity_id':q.id,'reference_company':target,'reason':reason,'reference_score':next((v for cid,v in scored if cid==target),''),'predicted_company_ids':';'.join(sorted(pred))})
    return results,errors,{'queries':len(queries),'pool_size':len(pool),'candidate_pairs':comparisons,'candidate_reduction':1-comparisons/(len(queries)*len(pool)),'blocking_recall_all':hits/len(queries),'blocking_recall_given_retrieval':hits/sum(truth[q.id] in pool for q in queries) if any(truth[q.id] in pool for q in queries) else None,'reference_available':sum(truth[q.id] in pool for q in queries),'review_pairs_at_default':reviews,'index_build_seconds':build,'blocking_and_scoring_seconds':perf_counter()-start}


def baselines(queries,companies,truth,threshold):
    pool={c.id for c in companies}; prepared=[(c.id,features(c)) for c in companies]
    exact=[]; fuzzy=[]; start=perf_counter()
    for i,q in enumerate(queries,1):
        a=features(q); ep=set(); fp=set()
        for cid,b in prepared:
            if a[0] and a[2] and a[0]==b[0] and a[2]==b[2]: ep.add(cid)
            if fast_score(a,b)>=threshold: fp.add(cid)
        exact.append(counts(ep,truth[q.id],pool)); fuzzy.append(counts(fp,truth[q.id],pool))
        if i%100==0: print(f'Exhaustive baseline: {i}/{len(queries)}',flush=True)
    return {'exact_name_and_postcode':metrics(exact),'exhaustive_fuzzy_same_weights_threshold':metrics(fuzzy),'pair_comparisons':len(queries)*len(companies),'combined_seconds':perf_counter()-start}


def corrupt(queries):
    rng=random.Random(81); out=[]
    for q in queries:
        mode=rng.randrange(3)
        if mode==0: out.append(q.model_copy(update={'postcode':''}))
        elif mode==1: out.append(q.model_copy(update={'address':''}))
        else:
            name=q.name
            if len(name)>3: name=name[1]+name[0]+name[2:]
            out.append(q.model_copy(update={'name':name}))
    return out


def run(directory,stage):
    directory=Path(directory); tuning,held,companies,truth=load(directory)
    if stage=='tune':
        thresholds=[65,70,75,80,85,90,95]
        rows,_,stats=blocked(tuning,companies,truth,thresholds)
        table={str(t):metrics(rows[t]) for t in thresholds}
        chosen=max(thresholds,key=lambda t:(table[str(t)]['f1'],t))
        result={'threshold':chosen,'weights_unchanged':[.55,.30,.15],'seed':42,'tuning_queries':len(tuning),'heldout_queries':len(held),'metrics_by_threshold':table,'blocking':stats,'fingerprint':fingerprint(directory)}
        (directory/'tuning.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    else:
        config=json.loads((directory/'tuning.json').read_text(encoding='utf-8'))
        if config['fingerprint']!=fingerprint(directory): raise ValueError('Frozen input changed; do not reuse tuning config')
        threshold=config['threshold']; thresholds=sorted({90,threshold})
        rows,errors,stats=blocked(held,companies,truth,thresholds)
        stress,_,stress_stats=blocked(corrupt(held),companies,truth,[threshold])
        result={'threshold_tuned':threshold,'heldout_queries':len(held),'blocking':stats,'default_worker_threshold_90':metrics(rows[90]),'tuned_offline':metrics(rows[threshold]),'bootstrap_95pct_query_intervals':interval(rows[threshold]),'baselines':baselines(held,companies,truth,threshold),'synthetic_corruption_separate':{'metrics':metrics(stress[threshold]),'blocking':stress_stats,'method':'seeded one of missing postcode, missing address, transposed initial characters'},'limitations':'Controlled pool includes retrieved true links; only linked charities; alternative legal identities not manually adjudicated. Bootstrap conditional on fixed pool; not population coverage. Tuned threshold offline only.'}
        write_csv(directory/'errors-private.csv',['charity_id','reference_company','reason','reference_score','predicted_company_ids'],errors[threshold])
        (directory/'evaluation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='fingerprint'},indent=2))


def main():
    p=argparse.ArgumentParser(); p.add_argument('directory'); p.add_argument('stage',choices=['tune','holdout']); a=p.parse_args(); run(a.directory,a.stage)

if __name__=='__main__': main()
