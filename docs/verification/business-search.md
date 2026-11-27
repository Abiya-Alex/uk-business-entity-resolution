# Business Search Verification

## Demonstration dataset

- Companies House records: 3
- FSA records processed: 3
- Stored matches: 1
- Quarantined records: 0

## Search results

| Search | Result |
|---|---|
| Green Cafe, TN9 2CD | Auto-match, score 100 |
| ABC Foods, TN9 1AB | No result |
| ABC Foods Limited, TN9 1AB | No result |
| Search without postcode | Required-field validation error |

## Identified limitation

The ABC Foods records appear to represent the same
business, but no match was returned by the API.

The root cause requires investigation across candidate
blocking, normalization, scoring and result persistence.

## Conclusion

The end-to-end infrastructure and business search
endpoint are operational. Matching correctness requires
further investigation and improvement in Phase B.
