"""Repeatable synthetic comparisons against a committed baseline."""
import argparse
import json
import platform
import string
import subprocess
import sys
import types
from time import perf_counter

from sqlalchemy import create_engine, text
from src import db, worker
from src.matching import CandidateIndex, Record, score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--size', type=int, default=5000)
    parser.add_argument('--queries', type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.queries <= args.size:
        parser.error('Require 1 <= queries <= size')
    # Execute the matching module from the trusted local baseline commit only.
    source = subprocess.check_output(['git', 'show', f'{args.baseline}:src/matching.py'], text=True)
    old = types.ModuleType('phase_a_matching')
    sys.modules[old.__name__] = old
    exec(compile(source, 'phase_a_matching.py', 'exec'), old.__dict__)
    records = []
    for i in range(args.size):
        prefix = ''.join(string.ascii_lowercase[(i // (26**j)) % 26] for j in range(3))
        records.append(Record(id=f'C{i:06d}', name=f'The {prefix}x Foods {i} Ltd',
                              address=f'{i+1} High Street', postcode=f'TN{i%20+1} {i%10}AB'))
    queries = [Record(id=f'F{i}', name=records[i].name.replace(' Ltd',' Limited'),
                      address=records[i].address.replace('Street','St.'), postcode=records[i].postcode)
               for i in range(args.queries)]
    def measure(index_type, scorer):
        start = perf_counter()
        index = index_type(records)
        build_ms = (perf_counter()-start)*1000
        start = perf_counter()
        count = hits = 0
        for i, query in enumerate(queries):
            candidates = index.candidates(query)
            count += len(candidates)
            hits += any(c.id == records[i].id for c in candidates)
            for candidate in candidates:
                scorer(query, candidate)
        return {'index_build_ms':round(build_ms,3), 'candidate_pairs':count,
                'blocking_recall_known_synthetic_pairs':hits/len(queries),
                'candidate_generation_and_scoring_ms':round((perf_counter()-start)*1000,3)}
    before = measure(old.CandidateIndex, old.score)
    after = measure(CandidateIndex, score)
    # Isolated in-memory database, never the Compose database or other projects.
    eng = create_engine('sqlite://')
    db.engine = worker.engine = eng
    db.init_db()
    with eng.begin() as conn:
        conn.execute(text('INSERT INTO companies(id,name,address,postcode) VALUES (:id,:name,:address,:postcode)'),
                     [r.model_dump() for r in records])
        conn.execute(text('UPDATE company_revision SET revision=1 WHERE id=1'))
    polls = 10
    start = perf_counter()
    for _ in range(polls):
        with eng.connect() as conn:
            old.CandidateIndex(old.Record(**dict(r)) for r in conn.execute(text('SELECT * FROM companies')).mappings())
    rebuild_ms = (perf_counter()-start)*1000
    cache = worker.IndexCache()
    start = perf_counter()
    for _ in range(polls):
        cache.get()
    cached_ms = (perf_counter()-start)*1000
    eng.dispose()
    report = {'dataset':'Synthetic stress workload: shared leading stop word; known positive for each query',
              'python':platform.python_version(), 'platform':platform.system(),
              'baseline_commit':subprocess.check_output(['git','rev-parse',args.baseline],text=True).strip(),
              'current_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
              'records':args.size, 'queries':args.queries, 'before':before, 'after':after,
              'candidate_reduction':1-after['candidate_pairs']/before['candidate_pairs'] if before['candidate_pairs'] else None,
              'index_cache_sqlite':{'unchanged_poll_count':polls,'baseline_rebuilds':polls,'actual_cached_builds':cache.builds,
                                    'baseline_ms':round(rebuild_ms,3),'cached_ms':round(cached_ms,3)},
              'limitations':'One run; timings depend on machine and workload. Synthetic recall is not real-data accuracy.'}
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
