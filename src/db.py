import os
from sqlalchemy import create_engine, inspect, text
from src.matching import name_key

engine = create_engine(os.getenv('DATABASE_URL','sqlite:///local.db'), pool_pre_ping=True)


def init_db() -> None:
    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            conn.execute(text("SELECT pg_advisory_xact_lock(712345)"))
        conn.execute(text('CREATE TABLE IF NOT EXISTS companies (id VARCHAR(100) PRIMARY KEY, name TEXT NOT NULL, address TEXT NOT NULL, postcode VARCHAR(20) NOT NULL)'))
        conn.execute(text('CREATE TABLE IF NOT EXISTS company_revision (id INTEGER PRIMARY KEY, revision BIGINT NOT NULL)'))
        conn.execute(text('INSERT INTO company_revision(id,revision) VALUES (1,0) ON CONFLICT(id) DO NOTHING'))
        conn.execute(text('CREATE TABLE IF NOT EXISTS matches (fsa_id VARCHAR(100), company_id VARCHAR(100), name TEXT NOT NULL, postcode VARCHAR(20), score FLOAT NOT NULL, status VARCHAR(30) NOT NULL, PRIMARY KEY(fsa_id, company_id))'))
        conn.execute(text('CREATE TABLE IF NOT EXISTS processed (job_id VARCHAR(100) PRIMARY KEY)'))
        conn.execute(text('CREATE TABLE IF NOT EXISTS quarantine (job_id VARCHAR(100) PRIMARY KEY, reason TEXT NOT NULL)'))
        conn.execute(text('CREATE INDEX IF NOT EXISTS idx_matches_postcode ON matches(postcode)'))
        # Existing local databases need an additive migration, not a volume reset.
        if 'normalized_name' not in {col['name'] for col in inspect(conn).get_columns('matches')}:
            conn.execute(text("ALTER TABLE matches ADD COLUMN normalized_name TEXT NOT NULL DEFAULT ''"))
            rows = conn.execute(text('SELECT fsa_id, company_id, name FROM matches')).mappings().all()
            for row in rows:
                conn.execute(text('UPDATE matches SET normalized_name=:n WHERE fsa_id=:f AND company_id=:c'),
                             {'n': name_key(row['name']), 'f': row['fsa_id'], 'c': row['company_id']})
        if engine.dialect.name == 'postgresql':
            conn.execute(text('CREATE INDEX IF NOT EXISTS idx_matches_search ON matches(postcode, normalized_name text_pattern_ops)'))
        else:
            conn.execute(text('CREATE INDEX IF NOT EXISTS idx_matches_search ON matches(postcode, normalized_name)'))
