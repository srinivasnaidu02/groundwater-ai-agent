"""Migration script to update Groundwater AI database schema.

Safely applies DDL changes to SQLite without dropping existing data.
Adds:
- Columns to groundwater_resources: source_agency, source_document, source_url, original_filename, sha256_checksum
- Tables: assessment_units, assessment_unit_categories, state_groundwater_resources, source_documents, import_audit_logs
Synchronizes canonical db (data/database/groundwater.db) and backend db (backend/data/database/groundwater.db).
"""
import sqlite3
import shutil
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
CANONICAL_DB = ROOT_DIR / "data" / "database" / "groundwater.db"
BACKEND_DB = ROOT_DIR / "backend" / "data" / "database" / "groundwater.db"


def run_migration(db_path: Path):
    print(f"Applying schema migration to: {db_path}")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Inspect existing columns in groundwater_resources
    cursor.execute("PRAGMA table_info(groundwater_resources)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    columns_to_add = [
        ("source_agency", "VARCHAR(200) DEFAULT 'CGWB'"),
        ("source_document", "VARCHAR(250)"),
        ("source_url", "TEXT"),
        ("original_filename", "VARCHAR(250)"),
        ("sha256_checksum", "VARCHAR(64)"),
    ]

    for col_name, col_type in columns_to_add:
        if col_name not in existing_cols:
            print(f"  Adding column {col_name} ({col_type}) to groundwater_resources")
            cursor.execute(f"ALTER TABLE groundwater_resources ADD COLUMN {col_name} {col_type}")
        else:
            print(f"  Column {col_name} already exists in groundwater_resources")

    # 2. Create assessment_units table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assessment_units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(150) NOT NULL,
        unit_type VARCHAR(50) DEFAULT 'Assessment Unit',
        district_id INTEGER REFERENCES districts(id),
        state_id INTEGER NOT NULL REFERENCES states(id),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_assessment_units_name ON assessment_units(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_assessment_units_district_id ON assessment_units(district_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_assessment_units_state_id ON assessment_units(state_id)")

    # 3. Create assessment_unit_categories table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assessment_unit_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year INTEGER NOT NULL,
        state_id INTEGER REFERENCES states(id),
        district_id INTEGER REFERENCES districts(id),
        assessment_unit_id INTEGER REFERENCES assessment_units(id),
        unit_name VARCHAR(150) NOT NULL,
        district_name VARCHAR(150),
        state_name VARCHAR(100),
        category VARCHAR(50) NOT NULL,
        source_file VARCHAR(250),
        source_url TEXT,
        verification_status VARCHAR(50) DEFAULT 'UNVERIFIED',
        is_verified BOOLEAN DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_auc_year ON assessment_unit_categories(year)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_auc_unit_name ON assessment_unit_categories(unit_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_auc_district_name ON assessment_unit_categories(district_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_auc_state_name ON assessment_unit_categories(state_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_auc_category ON assessment_unit_categories(category)")

    # 4. Create state_groundwater_resources table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS state_groundwater_resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        state_id INTEGER REFERENCES states(id),
        state_name VARCHAR(100) NOT NULL,
        year INTEGER NOT NULL,
        annual_recharge_bcm FLOAT,
        natural_discharges_bcm FLOAT,
        extractable_resources_bcm FLOAT,
        irrigation_extraction_bcm FLOAT,
        industrial_extraction_bcm FLOAT,
        domestic_extraction_bcm FLOAT,
        total_extraction_bcm FLOAT,
        net_future_availability_bcm FLOAT,
        stage_of_extraction_pct FLOAT,
        unit VARCHAR(20) DEFAULT 'Bcm',
        source_agency VARCHAR(200) DEFAULT 'CGWB / IN-GRES',
        source_file VARCHAR(250),
        source_url TEXT,
        verification_status VARCHAR(50) DEFAULT 'UNVERIFIED',
        is_verified BOOLEAN DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_sgr_state_name ON state_groundwater_resources(state_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_sgr_year ON state_groundwater_resources(year)")

    # 5. Create source_documents table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS source_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR(250) NOT NULL,
        agency VARCHAR(200) DEFAULT 'CGWB',
        publication_year INTEGER,
        assessment_year INTEGER,
        document_url TEXT,
        pdf_url TEXT,
        sha256 VARCHAR(64),
        verification_status VARCHAR(50) DEFAULT 'UNVERIFIED',
        verification_notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_source_docs_sha256 ON source_documents(sha256)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_source_docs_year ON source_documents(assessment_year)")

    # 6. Create import_audit_logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS import_audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dataset_name VARCHAR(200) NOT NULL,
        source_file VARCHAR(250),
        sha256 VARCHAR(64),
        assessment_year INTEGER,
        total_records INTEGER DEFAULT 0,
        verified_records INTEGER DEFAULT 0,
        unverified_records INTEGER DEFAULT 0,
        rejected_records INTEGER DEFAULT 0,
        synthetic_records INTEGER DEFAULT 0,
        audit_report_text TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()
    print("  Schema migration successfully committed.")


def sync_databases():
    if CANONICAL_DB.exists():
        BACKEND_DB.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(CANONICAL_DB, BACKEND_DB)
        print(f"Synchronized canonical db to {BACKEND_DB}")


if __name__ == "__main__":
    run_migration(CANONICAL_DB)
    sync_databases()

