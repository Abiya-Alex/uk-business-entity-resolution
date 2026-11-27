import os
from sqlalchemy import create_engine, text

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
