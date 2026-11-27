# Problem: linking charity register entries to company registrations

An analyst needs to find the Companies House legal company record corresponding to a Charity Commission entry. Legal suffixes, alternative names, contact versus registered office addresses and missing postcodes make exact matching unreliable. Candidate links are suggestions, not legal identity certification.

## Scope

England and Wales charity register entries with a usable official company reference; one charity per unique company in a seeded sample. Fetch reference companies and independently selected same-postcode candidates from Companies House. Hide the charity's company number from matching features. The candidate corpus is deliberately controlled; it does not represent the entire Companies House register.

## Requirements

Preserve source identifiers, normalize and block candidate pairs, score and classify matches, expose search and review, retry jobs without duplicate writes, quarantine invalid records, monitor and document failures. Compare exact and exhaustive fuzzy baselines and report retrieval failures, blocking recall, precision, recall, F1, uncertainty and error analysis on held-out data.

## Non-goals

Legal identity certification, production compliance decisions, nationwide search coverage, real-time reconciliation, public hosting, paid services. The API is local only. Official IDs are reference labels rather than independent human verification.
