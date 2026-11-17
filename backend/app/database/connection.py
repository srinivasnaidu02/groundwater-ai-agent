"""Database connection management."""
import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session
from pathlib import Path
from .models import Base

# Resolve database path
# Priority:
# 1. DATABASE_PATH env var
# 2. Repo root data/database/groundwater.db
# 3. Backend data/database/groundwater.db
env_db_path = os.environ.get("DATABASE_PATH")
if env_db_path:
    _abs = Path(env_db_path).resolve()
else:
    repo_root = Path(__file__).resolve().parents[3]
    candidate = repo_root / "data" / "database" / "groundwater.db"
    if candidate.exists() or candidate.parent.exists():
        _abs = candidate
    else:
        _abs = Path(__file__).resolve().parents[2] / "data" / "database" / "groundwater.db"

_abs.parent.mkdir(parents=True, exist_ok=True)

SYNC_DATABASE_URL = f"sqlite:///{_abs.as_posix()}"

# Sync engine
sync_engine = create_engine(
    SYNC_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)
SyncSession = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)


def run_migrations(engine):
    """Run table migrations safely on any engine."""
    migrations = {
        "source_datasets": {
            "publication_year": "VARCHAR(4)",
            "data_year": "VARCHAR(4)",
            "verification_status": "VARCHAR(20) NOT NULL DEFAULT 'UNVERIFIED'",
            "verification_evidence": "TEXT",
        },
        "groundwater_resources": {
            "is_verified": "BOOLEAN NOT NULL DEFAULT 0",
            "verification_status": "VARCHAR(20) NOT NULL DEFAULT 'UNVERIFIED'",
            "verification_evidence": "TEXT",
            "source_page_table": "VARCHAR(200)",
            "assessment_unit_name": "VARCHAR(150)",
            "assessment_unit_level": "VARCHAR(50) DEFAULT 'District'",
        },
    }
    inspector = inspect(engine)
    with engine.begin() as connection:
        for table_name, columns in migrations.items():
            if not inspector.has_table(table_name):
                continue
            existing_columns = {
                column["name"] for column in inspector.get_columns(table_name)
            }
            for column_name, column_type in columns.items():
                if column_name not in existing_columns:
                    connection.execute(text(
                        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                    ))


def init_db():
    """Create all tables and run migrations."""
    Base.metadata.create_all(bind=sync_engine)
    run_migrations(sync_engine)


def get_db():
    """FastAPI dependency: yields a db session."""
    db = SyncSession()
    try:
        yield db
    finally:
        db.close()


def get_sync_db() -> Session:
    """Returns a sync session for scripts."""
    return SyncSession()
