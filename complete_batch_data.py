"""Backup-first completion of AI model inputs using a separate, labelled demo table.

Run from the folder containing food_traceability.db:
    python complete_batch_data.py

This script does NOT fabricate stage events and does NOT overwrite journey records.
It stores synthetic demo values only in AI_Demo_Input, separate from actual traceability.
"""
from pathlib import Path
from datetime import datetime
import hashlib
import random
import shutil
import sqlite3

DB = Path(__file__).resolve().parent / "food_traceability.db"
if not DB.exists():
    raise FileNotFoundError(f"Database not found: {DB}\nPut this script beside food_traceability.db and run it there.")

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = DB.with_name(f"food_traceability_backup_ai_inputs_{stamp}.db")
shutil.copy2(DB, backup)
print(f"Backup created: {backup}")

conn = sqlite3.connect(str(DB))
conn.execute("PRAGMA foreign_keys = ON")

# Stable, reproducible demo inputs per batch. These are illustrative only, not food-safety guidance.
def demo_rng(batch_id):
    seed = int(hashlib.sha256(str(batch_id).encode("utf-8")).hexdigest()[:16], 16)
    return random.Random(seed)

try:
    conn.execute("BEGIN IMMEDIATE")
    batch_cols = {r[1] for r in conn.execute("PRAGMA table_info(Batch)")}
    if not {"batch_id", "crop_type", "harvest_date", "status"}.issubset(batch_cols):
        raise RuntimeError("Batch table is missing one or more expected columns: batch_id, crop_type, harvest_date, status")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS AI_Demo_Input (
            batch_id TEXT PRIMARY KEY,
            storage_temp_c REAL NOT NULL,
            storage_duration_hrs REAL NOT NULL,
            transit_time_hrs REAL NOT NULL,
            transit_temp_c REAL NOT NULL,
            humidity_pct REAL NOT NULL,
            prior_inspection_fail_count INTEGER NOT NULL,
            days_since_harvest REAL NOT NULL,
            source_note TEXT NOT NULL DEFAULT 'SYNTHETIC DEMO DATA - NOT MEASURED OR VERIFIED',
            updated_at TEXT NOT NULL,
            FOREIGN KEY (batch_id) REFERENCES Batch(batch_id) ON UPDATE CASCADE ON DELETE CASCADE
        )
    """)

    batches = conn.execute("SELECT batch_id FROM Batch ORDER BY batch_id").fetchall()
    if not batches:
        raise RuntimeError("No batches found in Batch table; nothing to complete.")

    # Preserve existing demo rows, so reruns do not silently change demo values.
    existing = {str(r[0]) for r in conn.execute("SELECT batch_id FROM AI_Demo_Input")}
    inserted = 0
    for (batch_id,) in batches:
        if str(batch_id) in existing:
            continue
        rng = demo_rng(batch_id)
        # Plausible-looking illustrative ranges for software demonstration only.
        values = (
            str(batch_id),
            round(rng.uniform(2.0, 9.0), 1),       # storage temperature °C
            round(rng.uniform(6.0, 72.0), 1),      # storage duration hours
            round(rng.uniform(0.5, 12.0), 1),       # transit duration hours
            round(rng.uniform(3.0, 14.0), 1),       # transit temperature °C
            round(rng.uniform(45.0, 92.0), 1),      # humidity %
            0,                                      # demo prior failure count when no inspection history exists
            round(rng.uniform(0.5, 14.0), 1),       # age in days if not calculable from recorded events
            "SYNTHETIC DEMO DATA - NOT MEASURED OR VERIFIED",
            datetime.now().isoformat(timespec="seconds"),
        )
        conn.execute("""
            INSERT INTO AI_Demo_Input (
                batch_id, storage_temp_c, storage_duration_hrs, transit_time_hrs,
                transit_temp_c, humidity_pct, prior_inspection_fail_count,
                days_since_harvest, source_note, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, values)
        inserted += 1

    # Verify every Batch has a demo-input row and all nine model inputs can be assembled
    missing = conn.execute("""
        SELECT COUNT(*) FROM Batch b LEFT JOIN AI_Demo_Input d ON CAST(d.batch_id AS TEXT)=CAST(b.batch_id AS TEXT)
        WHERE d.batch_id IS NULL OR d.storage_temp_c IS NULL OR d.storage_duration_hrs IS NULL
           OR d.transit_time_hrs IS NULL OR d.transit_temp_c IS NULL OR d.humidity_pct IS NULL
           OR d.prior_inspection_fail_count IS NULL OR d.days_since_harvest IS NULL
    """).fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM Batch").fetchone()[0]
    conn.commit()
    print(f"Batches found: {total}")
    print(f"New synthetic demo-input rows added: {inserted}")
    print(f"Existing demo-input rows preserved: {total - inserted}")
    print(f"Batches with missing demo-input fields: {missing}")
    print("Actual journey tables and Batch IDs were not modified.")
    print("Synthetic values are labelled and stored separately in AI_Demo_Input.")
    if missing:
        print("WARNING: Some rows remain incomplete. Check the AI_Demo_Input table and database schema.")
    else:
        print("SUCCESS: Every batch has a complete set of demo fallback inputs for all model fields.")
except Exception:
    conn.rollback()
    print("ERROR: Changes rolled back. Your backup remains available.")
    raise
finally:
    conn.close()
