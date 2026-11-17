import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

for db_rel in ["data/database/groundwater.db", "backend/data/database/groundwater.db"]:
    db_path = ROOT / db_rel
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("DELETE FROM groundwater_resources WHERE verification_status IN ('ESTIMATED', 'SYNTHETIC')")
    conn.commit()
    print(f"{db_rel}:")
    c.execute("SELECT count(*) FROM groundwater_resources")
    print("  Total authentic records:", c.fetchone()[0])
    c.execute("""
        SELECT y.year, g.verification_status, g.is_verified, count(*)
        FROM groundwater_resources g
        JOIN assessment_years y ON g.assessment_year_id = y.id
        GROUP BY y.year, g.verification_status, g.is_verified
        ORDER BY y.year
    """)
    for r in c.fetchall():
        print("   ", r)
    conn.close()

