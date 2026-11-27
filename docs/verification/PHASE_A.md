# Phase A - Baseline Verification

## Objective

Establish a reproducible local development environment
and verify the core business entity-resolution pipeline
before introducing performance improvements.

## Development Environment

- Python 3.12.10
- Windows
- Docker Compose
- PostgreSQL 16
- ElasticMQ
- FastAPI
- Prometheus
- Grafana

## Baseline Results

| Metric | Initial result | After initial corrections |
|---|---:|---:|
| Passing automated tests | 14 | 14 |
| Statement coverage | 78% | 78% |
| Ruff violations | 0 | 0 |
| Mypy errors | 1 | 0 |
| Docker startup | Failed | Successful |
| Running services | Not established | 6 |
| Processed demonstration jobs | Not measured | 3 |

## Database Verification

| Table | Record count |
|---|---:|
| companies | 3 |
| matches | 1 |
| processed | 3 |
| quarantine | 0 |

## Defect 1 - Incompatible Iterator Annotation

### Problem

Static type checking identified incompatible iterator
assignments in the data conversion module.

### Resolution

Introduced an explicit common iterator annotation.

### Verification

Mypy reported zero errors following the correction.
All 14 automated tests continued to pass.

## Defect 2 - Host Port Conflict

### Problem

Grafana attempted to bind to host port 3000, which was
already occupied by another local application.

### Resolution

Changed the Grafana host port to 3001 while retaining
the internal container port of 3000.

### Verification

All six services started successfully without requiring
the existing application to be stopped.

## Monitoring

The application health endpoint returned status ok.

Prometheus successfully scraped the application metrics
endpoint with target health reported as up.

The Grafana dashboard was accessible and displayed
application request activity.

## Known Limitations

- Only demonstration data has been processed.
- Real-world matching accuracy remains unmeasured.
- Only one demonstration match is stored; the matching
  decisions require further investigation.
- Ingestion and worker test coverage require improvement.
- A dependency deprecation warning remains.
- Formal performance and failure recovery tests are pending.
- Infrastructure is deployed locally, not on AWS.

## Next Steps

- Reuse the candidate index efficiently.
- Improve candidate blocking.
- Implement indexed database search.
- Quarantine malformed company records.
- Extend automated test coverage.
- Benchmark algorithm performance.
