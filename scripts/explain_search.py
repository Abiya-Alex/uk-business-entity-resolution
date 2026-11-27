"""PostgreSQL search plan comparison on temporary synthetic rows."""
from sqlalchemy import text
from src.db import engine

if engine.dialect.name != 'postgresql':
    raise SystemExit('Run inside the API container with PostgreSQL configured.')

with engine.connect() as conn:
    transaction = conn.begin()
    try:
        conn.execute(text('CREATE TEMP TABLE phase_b_plan (name TEXT NOT NULL, postcode TEXT NOT NULL, normalized_name TEXT NOT NULL, score FLOAT NOT NULL, status TEXT NOT NULL)'))
        conn.execute(text("INSERT INTO phase_b_plan SELECT 'Company ' || g, 'TN91AB', 'company ' || g, 100, 'auto_match' FROM generate_series(1,50000) g"))
        conn.execute(text('CREATE INDEX phase_b_postcode ON phase_b_plan(postcode)'))
        conn.execute(text('ANALYZE phase_b_plan'))
        before = "SELECT * FROM phase_b_plan WHERE postcode='TN91AB' AND lower(name) LIKE '%company 12345%' AND status IN ('auto_match','approved') ORDER BY score DESC LIMIT 50"
        after = "SELECT * FROM phase_b_plan WHERE postcode='TN91AB' AND normalized_name LIKE 'company 12345%' ESCAPE '!' AND status IN ('auto_match','approved') ORDER BY score DESC LIMIT 50"
        print('=== BASELINE: postcode index, substring search ===')
        for row in conn.execute(text('EXPLAIN (ANALYZE, BUFFERS) '+before)):
            print(row[0])
        conn.execute(text('CREATE INDEX phase_b_prefix ON phase_b_plan(postcode, normalized_name text_pattern_ops)'))
        conn.execute(text('ANALYZE phase_b_plan'))
        print('\n=== UPDATED: composite index, prefix search ===')
        for row in conn.execute(text('EXPLAIN (ANALYZE, BUFFERS) '+after)):
            print(row[0])
        print('\n=== ACTUAL MATCHES TABLE INDEXES ===')
        for row in conn.execute(text("SELECT indexname,indexdef FROM pg_indexes WHERE tablename='matches' AND schemaname=current_schema()")):
            print(row[0], row[1])
        print('\nSynthetic temporary rows only; no real-data performance claim. Prefix semantics differ from substring search.')
    finally:
        transaction.rollback()
