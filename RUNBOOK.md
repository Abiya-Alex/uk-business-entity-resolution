# Local operations runbook
- Start: `docker compose up --build -d`; inspect `docker compose ps` and `docker compose logs --tail=100 api worker queue db`.
- API unavailable: inspect /health, database health and logs; restart only affected service.
- Slow search: inspect Grafana and PostgreSQL EXPLAIN; measure before changing indexes.
- Worker stalled: inspect logs, check queue endpoint, DB connectivity, visibility timeout and job payload. Restart worker and confirm redelivery. Do not delete failed messages before preserving evidence.
- Dead letter: inspect via boto3 against localhost:9324 using dummy credentials; correct cause then manually requeue a copied payload; delete original only after confirming success. Keep queue local.
- Backup: `docker compose exec db pg_dump -U app business` (save output locally). Database reset with down -v is destructive.
- Stop: `docker compose down`; use named DB volume for persistence. No public hosting or cloud account.
