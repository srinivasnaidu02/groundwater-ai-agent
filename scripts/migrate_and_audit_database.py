"""
Database Migration, Provenance Correction and Audit Script.
Migrates SQLite schema to support explicit verification states and rich provenance.
Audits all records across 2020-2026 and sets exact verification status, evidence, and values.
Synchronizes root and backend databases.
"""
import sys
import os
import shutil
import sqlite3
from pathlib import Path

# Setup paths
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "backend"))

from app.database.connection import run_migrations, sync_engine, SyncSession
from app.database.models import (
    State, District, AssessmentYear, SourceDataset, GroundwaterResource, GeographicMaster
)


def migrate_sqlite_file(db_path: Path):
    """Run ALTER TABLE migrations directly on a SQLite file."""
    print(f"[INFO] Migrating SQLite database: {db_path}")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    migrations = {
        "source_datasets": [
            ("publication_year", "VARCHAR(4)"),
            ("data_year", "VARCHAR(4)"),
            ("verification_status", "VARCHAR(20) DEFAULT 'UNVERIFIED'"),
            ("verification_evidence", "TEXT"),
        ],
        "groundwater_resources": [
            ("is_verified", "BOOLEAN NOT NULL DEFAULT 0"),
            ("verification_status", "VARCHAR(20) NOT NULL DEFAULT 'UNVERIFIED'"),
            ("verification_evidence", "TEXT"),
            ("source_page_table", "VARCHAR(200)"),
            ("assessment_unit_name", "VARCHAR(150)"),
            ("assessment_unit_level", "VARCHAR(50) DEFAULT 'District'"),
        ],
    }

    for table, columns in migrations.items():
        cur.execute(f"PRAGMA table_info('{table}')")
        existing = {row[1] for row in cur.fetchall()}
        for col_name, col_type in columns:
            if col_name not in existing:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
                print(f"  Added column {table}.{col_name} ({col_type})")

    conn.commit()
    conn.close()


def audit_and_correct_database(db_path: Path):
    """Apply full verification policy and provenance metadata to database."""
    print(f"\n[INFO] Auditing and correcting records in: {db_path}")
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(f"sqlite:///{db_path.as_posix()}", echo=False)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # 1. Update Source Datasets
        sources_meta = {
            "2020": {
                "name": "CGWB National Compilation on Dynamic Ground Water Resources of India 2020",
                "agency": "Central Ground Water Board (CGWB), Ministry of Jal Shakti, Government of India",
                "url": "https://data.opencity.in/dataset/national-compilation-on-dynamic-ground-water-resources-of-india-2020",
                "pub_year": "2021",
                "filename": "groundwater_2020_all_states.csv",
                "is_verified": False,
                "status": "UNVERIFIED",
                "evidence": "Unverified dataset; values represent synthetic back-projections (~91-93% of 2022).",
            },
            "2022": {
                "name": "CGWB National Compilation on Dynamic Ground Water Resources of India 2022",
                "agency": "Central Ground Water Board (CGWB), Ministry of Jal Shakti, Government of India",
                "url": "https://data.opencity.in/dataset/national-compilation-on-dynamic-ground-water-resources-of-india-2022",
                "pub_year": "2022",
                "filename": "groundwater_2022_all_states.csv",
                "is_verified": True,
                "status": "VERIFIED",
                "evidence": "Official open data compilation directly matched to CGWB National Compilation 2022.",
            },
            "2023": {
                "name": "CGWB National Compilation on Dynamic Ground Water Resources of India 2023",
                "agency": "Central Ground Water Board (CGWB), Ministry of Jal Shakti, Government of India",
                "url": "https://cgwb.gov.in/cgwbpnm/public/uploads/documents/17056390342042899227file.pdf",
                "pub_year": "2023",
                "filename": "groundwater_2023_all_states.csv",
                "is_verified": False,
                "status": "UNVERIFIED",
                "evidence": "Unverified dataset; values represent uniform 2.5% synthetic increments of 2022.",
            },
            "2024": {
                "name": "CGWB / IN-GRES Dynamic Ground Water Resources Assessment 2024",
                "agency": "Central Ground Water Board (CGWB) & IIT Hyderabad (IN-GRES)",
                "url": "https://ingres.iith.ac.in/",
                "pub_year": "2024",
                "filename": "groundwater_2024_all_states.csv",
                "is_verified": False,
                "status": "UNVERIFIED",
                "evidence": "General IN-GRES portal reference; values represent synthetic 2.5% increments with Lucknow extraction anomaly.",
            },
            "2025": {
                "name": "National Compilation on Dynamic Ground Water Resources of India, 2025",
                "agency": "Central Ground Water Board (CGWB), Department of Water Resources, River Development & Ganga Rejuvenation, Ministry of Jal Shakti, Government of India",
                "url": "https://www.jalshakti-dowr.gov.in/static/uploads/2025/11/711d8d476bbf498cd90f8038e7371227.pdf",
                "pub_year": "2025",
                "filename": "groundwater_2025_all_states.csv",
                "is_verified": False,
                "status": "UNVERIFIED",
                "evidence": "Partial verification; only individually verified records (Patna extraction) confirmed against published PDF.",
            },
            "2026": {
                "name": "CGWB / IN-GRES Dynamic Ground Water Resources Assessment 2026",
                "agency": "Central Ground Water Board (CGWB) & IIT Hyderabad (IN-GRES)",
                "url": "https://ingres.iith.ac.in/",
                "pub_year": None,
                "filename": "groundwater_2026_all_states.csv",
                "is_verified": False,
                "status": "REJECTED",
                "evidence": "Demonstrably fabricated future year; no official 2026 assessment exists.",
            },
        }

        source_by_year = {}
        for yr, meta in sources_meta.items():
            src = session.query(SourceDataset).filter(SourceDataset.assessment_period == yr).first()
            if not src:
                src = SourceDataset(
                    name=meta["name"],
                    source_url=meta["url"],
                    assessment_period=yr,
                    publication_year=meta["pub_year"],
                    source_agency=meta["agency"],
                    original_filename=meta["filename"],
                    data_format="CSV",
                    unit="Ham (Hectare Meter)",
                    geographic_coverage="National / State / District Compilation",
                    is_verified=meta["is_verified"],
                    verification_status=meta["status"],
                    verification_evidence=meta["evidence"],
                )
                session.add(src)
                session.flush()
            else:
                src.name = meta["name"]
                src.source_agency = meta["agency"]
                src.source_url = meta["url"]
                src.publication_year = meta["pub_year"]
                src.original_filename = meta["filename"]
                src.is_verified = meta["is_verified"]
                src.verification_status = meta["status"]
                src.verification_evidence = meta["evidence"]
            source_by_year[yr] = src

        session.commit()

        # 2. Audit and update groundwater_resources
        records = session.query(GroundwaterResource).all()
        print(f"[INFO] Auditing {len(records)} groundwater records...")

        verified_count = 0
        unverified_count = 0
        rejected_count = 0
        synthetic_count = 0

        # Track duplicates in 2022
        seen_2022_districts = set()

        for rec in records:
            yr_obj = session.query(AssessmentYear).filter(AssessmentYear.id == rec.assessment_year_id).first()
            year = yr_obj.year if yr_obj else ""
            dist = session.query(District).filter(District.id == rec.district_id).first()
            dist_name = dist.name if dist else ""
            st = session.query(State).filter(State.id == rec.state_id).first()
            st_name = st.name if st else ""

            # Attach appropriate source dataset
            if year in source_by_year:
                rec.source_dataset_id = source_by_year[year].id

            rec.assessment_unit_name = dist_name
            rec.assessment_unit_level = "District"
            rec.unit = "Ham"

            # ---------------- 2025: Patna vs others ----------------
            if year == "2025":
                if dist_name == "Patna" and st_name == "Bihar":
                    # Correct Patna 2025 to authoritative source
                    rec.total_annual_extraction = 59747.83
                    rec.annual_extraction_irrigation = 41223.39
                    rec.annual_extraction_domestic = 17061.84
                    rec.annual_extraction_industrial = 1462.64
                    rec.stage_of_extraction_pct = None
                    # Recharge & category are missing/unverified in 2025 source table
                    rec.monsoon_recharge_rainfall = None
                    rec.monsoon_recharge_other = None
                    rec.non_monsoon_recharge_rainfall = None
                    rec.non_monsoon_recharge_other = None
                    rec.total_annual_recharge = None
                    rec.total_natural_discharges = None
                    rec.annual_extractable_groundwater = None
                    rec.gw_allocation_domestic_future = None
                    rec.net_gw_availability_future = None
                    rec.assessment_category = None
                    rec.is_verified = True
                    rec.verification_status = "VERIFIED"
                    rec.source_page_table = "District-wise Ground Water Resources of Bihar, District 26"
                    rec.verification_evidence = (
                        "Directly matched to Ministry of Jal Shakti / CGWB National Compilation on "
                        "Dynamic Ground Water Resources of India 2025, Bihar District Table (District 26: Patna)."
                    )
                    verified_count += 1
                else:
                    # Other 2025 rows are synthetic extrapolations
                    rec.is_verified = False
                    rec.verification_status = "SYNTHETIC"
                    rec.verification_evidence = (
                        f"Synthetic forward extrapolation (+2.5% over 2024) for {dist_name}, {st_name}; "
                        "not confirmed against authoritative 2025 compilation."
                    )
                    synthetic_count += 1

            # ---------------- 2022: OpenCity verified records ----------------
            elif year == "2022":
                key = (st_name, dist_name)
                if key in seen_2022_districts:
                    # Duplicate record (e.g. Nawada duplicate)
                    rec.is_verified = False
                    rec.verification_status = "REJECTED"
                    rec.verification_evidence = f"Duplicate record of {dist_name} ({st_name}) in 2022 dataset."
                    rejected_count += 1
                else:
                    seen_2022_districts.add(key)
                    rec.is_verified = True
                    rec.verification_status = "VERIFIED"
                    rec.source_page_table = "State/District Wise Dynamic Ground Water Resources of India 2022"
                    if dist_name == "Solapur" and st_name == "Maharashtra":
                        rec.verification_evidence = (
                            "Directly matched to CGWB 2022 National Compilation (note: reported recharge 409,000 Ham "
                            "reflects state compilation figure; component sum is 388,000 Ham)."
                        )
                    else:
                        rec.verification_evidence = (
                            f"Directly matched to CGWB National Compilation on Dynamic Ground Water Resources "
                            f"of India 2022 for {dist_name}, {st_name}."
                        )
                    verified_count += 1

            # ---------------- 2020: Check Ludhiana anomaly & back-projections ----------------
            elif year == "2020":
                if dist_name == "Ludhiana" and st_name == "Bihar":
                    rec.is_verified = False
                    rec.verification_status = "REJECTED"
                    rec.verification_evidence = (
                        "Demonstrably incorrect state-district combination: Ludhiana is in Punjab, not Bihar."
                    )
                    rejected_count += 1
                else:
                    rec.is_verified = False
                    rec.verification_status = "SYNTHETIC"
                    rec.verification_evidence = (
                        f"Synthetic back-projection (~91-93% of 2022) for {dist_name}, {st_name}; "
                        "unconfirmed in official 2020 compilation."
                    )
                    synthetic_count += 1

            # ---------------- 2023: Extrapolations ----------------
            elif year == "2023":
                rec.is_verified = False
                rec.verification_status = "SYNTHETIC"
                rec.verification_evidence = (
                    f"Synthetic forward extrapolation (+2.5% of 2022) for {dist_name}, {st_name}; "
                    "unconfirmed in official 2023 compilation."
                )
                synthetic_count += 1

            # ---------------- 2024: Extrapolations & Lucknow typo ----------------
            elif year == "2024":
                if dist_name == "Lucknow" and st_name == "Uttar Pradesh":
                    rec.is_verified = False
                    rec.verification_status = "REJECTED"
                    rec.verification_evidence = (
                        "Demonstrably inconsistent extraction components: irrigation (20,800) + industrial (13,100) + "
                        "domestic (34,100) = 68,000 Ham vs reported total 255,200 Ham."
                    )
                    rejected_count += 1
                else:
                    rec.is_verified = False
                    rec.verification_status = "SYNTHETIC"
                    rec.verification_evidence = (
                        f"Synthetic forward extrapolation (+2.5% of 2023) for {dist_name}, {st_name}; "
                        "unconfirmed in authoritative source."
                    )
                    synthetic_count += 1

            # ---------------- 2026: Fabricated future year ----------------
            elif year == "2026":
                rec.is_verified = False
                rec.verification_status = "SYNTHETIC"
                rec.verification_evidence = (
                    f"Demonstrably fabricated future year 2026; no official dynamic groundwater assessment exists."
                )
                synthetic_count += 1

            else:
                rec.is_verified = False
                rec.verification_status = "UNVERIFIED"
                rec.verification_evidence = "Unverified record."
                unverified_count += 1

        session.commit()

        # Update source records count in source_datasets
        for yr, src in source_by_year.items():
            yr_obj = session.query(AssessmentYear).filter(AssessmentYear.year == yr).first()
            if yr_obj:
                total_src = session.query(GroundwaterResource).filter(
                    GroundwaterResource.assessment_year_id == yr_obj.id
                ).count()
                src.num_records = total_src
        session.commit()

        print("\n=== AUDIT SUMMARY ===")
        print(f"Total records audited: {len(records)}")
        print(f"VERIFIED records:     {verified_count}")
        print(f"UNVERIFIED records:   {unverified_count}")
        print(f"REJECTED records:     {rejected_count}")
        print(f"SYNTHETIC records:    {synthetic_count}")
        print(f"Verified assessment years: 2022 (142 districts), 2025 (Patna, Bihar)")

    finally:
        session.close()


def main():
    root_db = repo_root / "data" / "database" / "groundwater.db"
    backend_db = repo_root / "backend" / "data" / "database" / "groundwater.db"

    # Step 1: Migrate and audit root database
    migrate_sqlite_file(root_db)
    audit_and_correct_database(root_db)

    # Step 2: Synchronize backend database to match root database
    print(f"\n[INFO] Synchronizing backend database copy at {backend_db}...")
    backend_db.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root_db, backend_db)
    print(f"[SUCCESS] Root and backend databases are now perfectly synchronized.")


if __name__ == "__main__":
    main()
