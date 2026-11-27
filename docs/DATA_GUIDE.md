# Real data workflow
1. Download Companies House basic company data from https://download.companieshouse.gov.uk/en_output.html (bulk CSV ZIP). Extract locally. For large files choose the split download and process one part at a time; do not claim full regional coverage from one part.
2. Obtain FSA data using https://ratings.food.gov.uk/open-data or https://api.ratings.food.gov.uk/help . Save JSON establishments for selected local authorities (the converter expects a JSON array or object with `establishments`). Follow API pagination and attribution terms. XML downloads must be converted separately. Verify actual schema before import.
3. Create data/real locally. Run:
```
python -m src.convert companies PATH_TO_COMPANIES.csv data/real/companies.csv --areas TN ME
python -m src.convert fsa PATH_TO_FSA.json data/real/fsa.csv --areas TN ME
python -m src.profile_data data/real/companies.csv data/real/fsa.csv
```
Use a single bounded regional sample, record retrieval dates and row counts, and inspect address and postcode coverage. Copy the canonical files into running containers with `docker compose cp data/real api:/app/data/real`, then `docker compose exec api python -m src.ingest data/real/companies.csv data/real/fsa.csv`. Import into a clean snapshot if you already ran demo data.
4. Copy labels_template.csv into tuning.csv and heldout.csv under data/real. Select ~200 pairs total including plausible matches, hard negatives, different names/addresses and true matches missed by blocking. Avoid splitting pairs involving the same entity across tuning and test. Confirm matches using evidence of legal entity/trading premise relationships; mark uncertain pairs separately and exclude with documented counts. Label 1 or 0 only when evidence supports it. Keep a private evidence log. A second reviewer is useful if available.
5. Tune score weights/thresholds using tuning pairs only. Freeze the configuration then run `python -m src.evaluate data/real/heldout.csv`. Report sample composition, review count, precision/recall/F1 for auto-match and limits of sampling; this is not an unbiased estimate of all possible pairs without representative sampling. Do not use the held-out results to tune again.

Optional candidate sample: `python -m src.sample_pairs data/real/companies.csv data/real/fsa.csv data/real/sample.csv --count 200`. This is a convenience sample, not representative ground truth; add independently discovered missed-block examples and separate entities into tuning/holdout.
