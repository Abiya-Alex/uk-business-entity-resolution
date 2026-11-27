# ADR 003: deterministic matching
Use normalized name and postcode district blocking, weighted fuzzy scoring (55 name, 30 address, 15 exact postcode). Initial thresholds 90 and 65 are hypotheses, not calibrated probabilities. Compare against exact match baseline; tune only on tuning labels. Consider ambiguous candidates and missed blocks. Simpler and auditable versus ML.
