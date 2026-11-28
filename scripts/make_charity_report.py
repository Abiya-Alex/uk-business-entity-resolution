"""Create aggregate-only Markdown from locally measured evaluation artifacts."""
import argparse
import json
import platform
import subprocess
from pathlib import Path
from datetime import datetime,timezone

p=argparse.ArgumentParser(); p.add_argument('directory'); p.add_argument('--hardware',required=True); a=p.parse_args(); d=Path(a.directory)
def load(name): return json.loads((d/name).read_text(encoding='utf-8-sig'))
profile=load('profile.json'); fetch=load('fetch-report.json'); ev=load('evaluation.json'); live=load('live-audit.json'); tuning=load('tuning.json')
sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
lines=['# Phase C — controlled charity/company linkage evaluation','',f'- Code commit: `{sha}`',f'- Report UTC: {datetime.now(timezone.utc).isoformat()}',f'- Hardware: {a.hardware}',f'- Python: {platform.python_version()}; OS: {platform.system()} {platform.release()}',f'- Charity extract dates: {profile["extract_dates"]}',f'- Companies House cache retrieval window UTC: {fetch["cache_retrieval_window_utc"]}', '', '## Data profile', '', '| Measure | Count |','|---|---:|']
for k,v in profile.items():
    if isinstance(v,int): lines.append(f'| {k} | {v} |')
for k in ('requested_linked','retrieved_linked','unavailable_or_invalid','distractors','candidate_pool','candidate_missing_address','candidate_missing_postcode','postcode_searches'): lines.append(f'| {k} | {fetch[k]} |')
lines+=['','## Held-out results','',f'Tuning queries: {tuning["tuning_queries"]}; held-out queries: {ev["heldout_queries"]}; frozen threshold: {ev["threshold_tuned"]}. Weights unchanged.','', '| Method | Precision | Recall | F1 | TP | FP | FN |','|---|---:|---:|---:|---:|---:|---:|']
for label,m in [('Exact name + postcode',ev['baselines']['exact_name_and_postcode']),('Exhaustive fuzzy',ev['baselines']['exhaustive_fuzzy_same_weights_threshold']),('Blocked default 90',ev['default_worker_threshold_90']),('Blocked tuned offline',ev['tuned_offline']),('Corrupted held-out (separate stress test)',ev['synthetic_corruption_separate']['metrics'])]:
    lines.append(f'| {label} | {m["precision"]:.4f} | {m["recall"]:.4f} | {m["f1"]:.4f} | {m["tp"]} | {m["fp"]} | {m["fn"]} |')
lines+=['','## Blocking and uncertainty','',f'- Blocking recall (all queries): {ev["blocking"]["blocking_recall_all"]:.4f}',f'- Blocking recall conditional on retrieval: {ev["blocking"]["blocking_recall_given_retrieval"]}',f'- Candidate comparisons: {ev["blocking"]["candidate_pairs"]}; reduction: {ev["blocking"]["candidate_reduction"]:.4f}',f'- Exhaustive comparisons: {ev["baselines"]["pair_comparisons"]}',f'- Blocking/scoring seconds: {ev["blocking"]["blocking_and_scoring_seconds"]:.3f}; exhaustive plus exact baseline seconds: {ev["baselines"]["combined_seconds"]:.3f}',f'- Query-bootstrap 95% intervals: {ev["bootstrap_95pct_query_intervals"]}', '', '## Live pipeline (default threshold, all imported queries)', '', '```json',json.dumps(live,indent=2),'```','', '## Limitations','',ev['limitations'],'Charity contact addresses may differ from registered offices. Companies House search location is not a geographic radius; only exact postcode returns were accepted as distractors. Retrieval failures are counted separately and remain false negatives in unconditional recall. Official identifiers supply reference labels, not human verification. A different company number is a non-reference prediction, not proof that no legal relationship exists. No nationwide independent search, production or AWS claims.','', '## Sources','', '- Charity Commission for England and Wales, public register extract: https://register-of-charities.charitycommission.gov.uk/en/register/full-register-download', '- Companies House Public Data API: https://developer.company-information.service.gov.uk/', '- Review source terms and Open Government Licence exceptions before redistribution. Raw records, contact details, credentials and truth labels are not published.','', '## Error analysis','', 'Pending manual inspection; add aggregate observations from 30–50 errors (or all if fewer) before closing Phase C. Do not publish identifiable record details.']
Path('docs/RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('Wrote docs/RESULTS.md; manual error analysis still required.')

profile_text = '# Charity and company data profile\n\n' + '\n'.join(lines[3:8]) + '\n\n' + '\n'.join(lines[lines.index('## Data profile'):lines.index('## Held-out results')]) + '\nRegistration statuses: ' + str(profile['registration_statuses']) + '\n\nOne representative per company; seeded sample; missing counts refer to the eligible pre-deduplication rows unless otherwise stated. Contact and registered office addresses may differ. No raw rows published.\n'
Path('docs/data-profile.md').write_text(profile_text,encoding='utf-8')
