# Phase C — controlled charity/company linkage evaluation

- Code commit: `92b909cb781bedaf23d08698253b898c8b9504b7`
- Report UTC: 2026-11-28T19:44:03.319963+00:00
- Hardware: 11th Gen Intel(R) Core(TM) i5-1135G7 @ 2.40GHz; 15.7 GB RAM
- Python: 3.12.10; OS: Windows 11
- Charity extract dates: {'2026-11-27 00:00:00.0000000': 397443}
- Companies House cache retrieval window UTC: ['2026-11-27T21:18:06.098413+00:00', '2026-11-28T19:01:51.050989+00:00']

## Data profile

| Measure | Count |
|---|---:|
| rows | 397443 |
| registered | 184582 |
| registered_nonblank_company_number | 31233 |
| usable_rows | 31213 |
| missing_address | 17 |
| missing_postcode | 658 |
| invalid_number_format | 20 |
| unique_eligible_companies | 31147 |
| selected | 5000 |
| seed | 42 |
| requested_linked | 5000 |
| retrieved_linked | 4974 |
| unavailable_or_invalid | 26 |
| distractors | 3191 |
| candidate_pool | 8165 |
| candidate_missing_address | 42 |
| candidate_missing_postcode | 48 |
| postcode_searches | 500 |

## Held-out results

Tuning queries: 3000; held-out queries: 2000; frozen threshold: 65. Weights unchanged.

| Method | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| Exact name + postcode | 0.9993 | 0.7155 | 0.8339 | 1431 | 1 | 569 |
| Exhaustive fuzzy | 0.9142 | 0.9430 | 0.9284 | 1886 | 177 | 114 |
| Blocked default 90 | 0.9686 | 0.6010 | 0.7417 | 1202 | 39 | 798 |
| Blocked tuned offline | 0.9155 | 0.9430 | 0.9291 | 1886 | 174 | 114 |
| Corrupted held-out (separate stress test) | 0.9588 | 0.8145 | 0.8808 | 1629 | 70 | 371 |

## Blocking and uncertainty

- Blocking recall (all queries): 0.9900
- Blocking recall conditional on retrieval: 0.9924812030075187
- Candidate comparisons: 22195; reduction: 0.9986
- Exhaustive comparisons: 16330000
- Blocking/scoring seconds: 3.566; exhaustive plus exact baseline seconds: 62.752
- Query-bootstrap 95% intervals: {'precision': [0.8843283582089553, 0.9407630522088354], 'recall': [0.9325, 0.9525], 'f1': [0.9127290260366442, 0.9423410047018065]}

## Live pipeline (default threshold, all imported queries)

```json
{
  "companies": 8165,
  "processed": 5000,
  "matches": 5234,
  "quarantine": 0,
  "auto_matches": 3153,
  "review_matches": 2081,
  "distinct_auto_query_ids": 3066,
  "jobs": {
    "ApproximateNumberOfMessages": "0",
    "ApproximateNumberOfMessagesNotVisible": "0",
    "ApproximateNumberOfMessagesDelayed": "0"
  },
  "dead": {
    "ApproximateNumberOfMessages": "0",
    "ApproximateNumberOfMessagesNotVisible": "0",
    "ApproximateNumberOfMessagesDelayed": "0"
  }
}
```

## Limitations

Controlled pool includes retrieved true links; only linked charities; alternative legal identities not manually adjudicated. Bootstrap conditional on fixed pool; not population coverage. Tuned threshold offline only.
Charity contact addresses may differ from registered offices. Companies House search location is not a geographic radius; only exact postcode returns were accepted as distractors. Retrieval failures are counted separately and remain false negatives in unconditional recall. Official identifiers supply reference labels, not human verification. A different company number is a non-reference prediction, not proof that no legal relationship exists. No nationwide independent search, production or AWS claims.

## Sources

- Charity Commission for England and Wales, public register extract: https://register-of-charities.charitycommission.gov.uk/en/register/full-register-download
- Companies House Public Data API: https://developer.company-information.service.gov.uk/
- Review source terms and Open Government Licence exceptions before redistribution. Raw records, contact details, credentials and truth labels are not published.

## Automated error analysis

All 194 error entries were analysed using deterministic
feature-level diagnostics instead of manual sampling.
No manual adjudication was performed.

### Error categories

| Category | Count |
|---|---:|
| extra_auto_matches | 80 |
| below_threshold | 94 |
| blocking_miss | 15 |
| retrieval_missing | 5 |

### Reference-pair diagnostic flags

| Diagnostic flag | Count |
|---|---:|
| no_clear_feature_disagreement | 60 |
| low_address_similarity | 103 |
| postcode_disagreement | 83 |
| missing_address | 20 |
| missing_postcode | 26 |
| low_name_similarity | 28 |
| reference_unavailable | 5 |

### Feature similarity

- Available reference pairs analysed: 189.
- Mean name similarity: 91.36.
- Mean address similarity: 58.44.
- Unresolved charity identifiers: 0.

### Competing candidate analysis

| Diagnostic flag | Count |
|---|---:|
| similar_address | 122 |
| same_postcode | 168 |
| similar_name | 40 |

The diagnostics covered 170 competing pairs.
The evaluation reported 174 false-positive pairs overall.
Complete false-positive diagnostic coverage is not claimed.

### Engineering implications

- Address and postcode disagreements are prominent among missed links.
- Shared postcodes are common among competing predictions.
- Ranked matching and ambiguity handling should be prioritized.
- Missing-field-aware scoring should be investigated.

### Diagnostic methodology and limitations

Diagnostics use normalized RapidFuzz token-sort similarity
and exact normalized postcode agreement.
Low name similarity is defined as below 80;
low address similarity is defined as below 70.
Competitor similarity is flagged at 80 or above.

Diagnostic flags may overlap. Similarities are descriptive
heuristics rather than original matcher scores or verified
root causes. Findings are conditional on the analysed errors
and should not be generalized to the entire charity population.
The frozen held-out evaluation was not modified.

Reproduce with:

```powershell
python -m scripts.analyze_charity_errors "$full"
```
