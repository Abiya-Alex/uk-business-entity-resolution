# ADR 001: PostgreSQL
Use relational tables, composite primary keys and transactions to enforce idempotency. Alternative: SQLite (used for lightweight tests), less suitable for multiple concurrent workers. Trade-off: a separate database container and schema migration work. Revisit after benchmarking.
