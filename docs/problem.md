# Customer problem
A compliance analyst needs to locate potential links between legal company registrations and food trading premises without manually comparing thousands of records. Inconsistent suffixes, addresses, missing fields and multiple premises make exact matching unreliable.

## Requirements
Ingest two public datasets; normalize and block candidate pairs; score and classify matches; expose search and review via REST; preserve source IDs; retry messages without duplicate writes; quarantine invalid records; monitor and document failures.

## Non-goals
Legal identity certification, global coverage, public hosting, real-time updates, ML and paid services. All links require appropriate verification before compliance decisions.
