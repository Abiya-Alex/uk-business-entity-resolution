# Phase B engineering decisions

## Candidate freshness

The original worker loads companies before the long poll. If an import commits during that wait, a newly received job may be processed against a stale index and marked processed. The regression test reproduces that ordering; it does not prove the historical ABC incident had exactly that cause. The original score for the ABC fixture is 100.

Use a revision row updated in the same transaction as changed company records, and cache the candidate index per worker. Check freshness after receiving a batch. A repeated identical import does not advance the revision. Changes made outside the ingestion path are not tracked. Index refresh does not reconcile previously processed jobs or stale matches; snapshot reconciliation remains later work.

## Blocking and normalization

Use Unicode normalization, trailing legal-suffix removal, stop-word-aware four-character name prefixes, exact postcode and prefix/district keys. Rank candidates by stronger geographic/name agreement and cap at 200. This limits fuzzy scoring calls, but large posting lists can still cost time and memory. The cap can omit genuine matches. Tune only with labelled evidence; the scoring weights and thresholds remain unchanged. Real-data evaluation should pass the complete canonical company file to the evaluator so the cap is reflected.

## Database search

Persist the normalized name of each FSA match and index `(postcode, normalized_name text_pattern_ops)` in PostgreSQL. Escape LIKE metacharacters and use prefix search; arbitrary substring queries no longer work. The additive migration backfills existing records. It does not recompute matching scores. The demonstration EXPLAIN script uses a temporary synthetic table and rolls back.

## Bad input

Quarantine malformed company rows with a reason and stable content hash, without including raw source values in the reason. Valid rows and revision changes commit together. Database failures still abort the transaction. Identical invalid rows deduplicate in quarantine. Missing usable company IDs/names are rejected; absent address/postcode can still be valid inputs. This applies to canonical ingestion, not all possible corruption in upstream conversion.

## Verification

The CI matrix exercises Python 3.12 on Linux and Windows, including lint, type checks and an 85% statement-coverage gate. Unit and SQLite-backed tests are not proof of PostgreSQL or queue integration. Use the local Compose service and inspect actual results. Credentials in the Compose and queue configuration are local demonstration placeholders; do not reuse or expose them. No AWS deployment has been performed.
