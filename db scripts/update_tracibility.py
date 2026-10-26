import sqlite3
import shutil
from pathlib import Path
from datetime import date, datetime, timedelta
from collections import Counter

DB = Path("food_traceability.db")

# Exact target distribution: 51 batches
TARGET_COUNTS = {
    "Delivered": 15,
    "Retail": 14,
    "Sold": 10,
    "Recalled": 3,
    "Harvested": 3,
    "Processing": 2,
    "Stored": 2,
    "In_Transit": 2,
}

# Stages expected to have records at each status.
STAGE_PLAN = {
    "Harvested": [],
    "Processing": ["collection", "processing"],
    "Stored": ["collection", "processing", "storage"],
    "In_Transit": [
        "collection", "processing", "storage", "transport"
    ],
    "Delivered": [
        "collection", "processing", "storage", "transport"
    ],
    "Retail": [
        "collection", "processing", "storage", "transport", "retail"
    ],
    "Sold": [
        "collection", "processing", "storage", "transport", "retail"
    ],
    "Recalled": [
        "collection", "processing", "storage", "transport", "retail"
    ],
}

TABLES = {
    "collection": "Collection_Record",
    "processing": "Processing_Record",
    "storage": "Storage_Record",
    "transport": "Transport_Log",
    "retail": "Retail_Inventory",
}

if not DB.exists():
    raise FileNotFoundError(
        f"Database not found: {DB.resolve()}"
    )

# Make a uniquely named backup before any modifications.
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP = DB.with_name(f"food_traceability_backup_{timestamp}.db")
shutil.copy2(DB, BACKUP)
print(f"Backup created: {BACKUP}")

conn = sqlite3.connect(DB)
conn.execute("PRAGMA foreign_keys = ON")


def has_record(table, batch_id):
    return conn.execute(
        f'SELECT 1 FROM "{table}" WHERE batch_id = ? LIMIT 1',
        (batch_id,)
    ).fetchone() is not None


def get_reference_id(table, id_column):
    row = conn.execute(
        f'SELECT "{id_column}" FROM "{table}" '
        f'ORDER BY "{id_column}" LIMIT 1'
    ).fetchone()

    if row is None:
        raise RuntimeError(
            f"No reference record exists in {table}."
        )

    return row[0]


def add_missing_stage_records(batch, references, inserted):
    batch_id, crop, harvest_str, quantity, status = batch

    harvest = date.fromisoformat(harvest_str)
    qty = float(quantity)
    completed = STAGE_PLAN[status]

    # All dates and measurements below are illustrative demo data.
    dates = {
        "collection": harvest + timedelta(days=1),
        "processing": harvest + timedelta(days=2),
        "storage_in": harvest + timedelta(days=3),
        "storage_out": harvest + timedelta(days=4),
        "dispatch": harvest + timedelta(days=5),
        "arrival": harvest + timedelta(days=6),
        "retail": harvest + timedelta(days=7),
    }

    if "collection" in completed:
        if not has_record("Collection_Record", batch_id):
            conn.execute("""
                INSERT INTO Collection_Record
                    (batch_id, center_id, received_date, grade)
                VALUES (?, ?, ?, ?)
            """, (
                batch_id,
                references["center"],
                dates["collection"].isoformat(),
                "Grade A (synthetic demo)"
            ))
            inserted["Collection_Record"] += 1

    if "processing" in completed:
        if not has_record("Processing_Record", batch_id):
            conn.execute("""
                INSERT INTO Processing_Record
                    (batch_id, plant_id, process_date, process_type,
                     output_qty_kg)
                VALUES (?, ?, ?, ?, ?)
            """, (
                batch_id,
                references["plant"],
                dates["processing"].isoformat(),
                f"{crop} sorting and packing (demo)",
                round(qty * 0.98, 2)
            ))
            inserted["Processing_Record"] += 1

    if "storage" in completed:
        if not has_record("Storage_Record", batch_id):
            conn.execute("""
                INSERT INTO Storage_Record
                    (batch_id, warehouse_id, in_date, out_date,
                     temperature_c, humidity_pct)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                batch_id,
                references["warehouse"],
                dates["storage_in"].isoformat(),
                dates["storage_out"].isoformat(),
                5.0,
                65.0
            ))
            inserted["Storage_Record"] += 1

    if "transport" in completed:
        if not has_record("Transport_Log", batch_id):
            conn.execute("""
                INSERT INTO Transport_Log
                    (batch_id, transporter_id, origin, destination,
                     dispatch_time, arrival_time, transit_temp_c)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                batch_id,
                references["transporter"],
                "Erode, Tamil Nadu",
                "Chennai, Tamil Nadu",
                f'{dates["dispatch"].isoformat()} 08:00:00',
                f'{dates["arrival"].isoformat()} 14:00:00',
                8.0
            ))
            inserted["Transport_Log"] += 1

    if "retail" in completed:
        if not has_record("Retail_Inventory", batch_id):
            conn.execute("""
                INSERT INTO Retail_Inventory
                    (batch_id, store_id, received_date,
                     quantity_kg, unit_price)
                VALUES (?, ?, ?, ?, ?)
            """, (
                batch_id,
                references["store"],
                dates["retail"].isoformat(),
                round(qty * 0.95, 2),
                40.0
            ))
            inserted["Retail_Inventory"] += 1

    # Add an inspection record if none exists for this batch.
    # Recalled batches get a review flag, not a claim of actual contamination.
    if status != "Harvested" and not has_record("Inspection", batch_id):
        if status == "Recalled":
            stage = "Recall Review"
            result = "Review Required"
            note = (
                "Synthetic demo recall flag. Requires verification; "
                "not evidence of actual contamination."
            )
        else:
            stage = completed[-1].title() if completed else "Processing"
            result = "Demo Pass"
            note = (
                "Synthetic demonstration inspection; "
                "not a real-world inspection."
            )

        conn.execute("""
            INSERT INTO Inspection
                (batch_id, stage, inspector_name, inspection_date,
                 result, contamination_type, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            batch_id,
            stage,
            "Demo Inspector",
            dates["arrival"].isoformat(),
            result,
            "Not assessed",
            note
        ))
        inserted["Inspection"] += 1


try:
    batches = conn.execute("""
        SELECT batch_id, crop_type, harvest_date, quantity_kg, status
        FROM Batch
        ORDER BY batch_id
    """).fetchall()

    if len(batches) != sum(TARGET_COUNTS.values()):
        raise RuntimeError(
            f"Expected {sum(TARGET_COUNTS.values())} batches, "
            f"but found {len(batches)}. No changes were committed."
        )

    # Keep batches that already have journey records in Sold,
    # so existing downstream records aren't contradicted by an earlier status.
    journey_tables = list(TABLES.values()) + ["Inspection"]

    existing_journey_batches = set()
    for table in journey_tables:
        rows = conn.execute(
            f'SELECT DISTINCT batch_id FROM "{table}"'
        ).fetchall()
        existing_journey_batches.update(row[0] for row in rows)

    if len(existing_journey_batches) > TARGET_COUNTS["Sold"]:
        raise RuntimeError(
            f"{len(existing_journey_batches)} batches already have journey "
            f"records, but only {TARGET_COUNTS['Sold']} Sold slots are "
            "available. No changes were committed. Review existing records "
            "before choosing a different distribution."
        )

    batch_ids = {b[0] for b in batches}
    unknown_ids = existing_journey_batches - batch_ids

    if unknown_ids:
        raise RuntimeError(
            f"Journey records reference unknown batches: {unknown_ids}"
        )

    # Reserve Sold for batches with existing stage records.
    assignment = {
        batch_id: "Sold" for batch_id in existing_journey_batches
    }

    remaining = TARGET_COUNTS.copy()
    remaining["Sold"] -= len(assignment)

    # Assign the remaining statuses deterministically.
    unassigned_batches = [
        batch for batch in batches if batch[0] not in assignment
    ]

    ordered_statuses = [
        "Delivered", "Retail", "Sold", "Recalled",
        "Harvested", "Processing", "Stored", "In_Transit"
    ]

    index = 0
    for status in ordered_statuses:
        for _ in range(remaining[status]):
            assignment[unassigned_batches[index][0]] = status
            index += 1

    if index != len(unassigned_batches):
        raise RuntimeError(
            "Status allocation mismatch. No changes were committed."
        )

    # Validate reference tables before inserting anything.
    references = {
        "center": get_reference_id("Collection_Center", "center_id"),
        "plant": get_reference_id("Processing_Plant", "plant_id"),
        "warehouse": get_reference_id("Warehouse", "warehouse_id"),
        "transporter": get_reference_id("Transporter", "transporter_id"),
        "store": get_reference_id("Retail_Store", "store_id"),
    }

    # Update statuses, preserving batch IDs and other batch details.
    for batch_id, status in assignment.items():
        conn.execute(
            "UPDATE Batch SET status = ? WHERE batch_id = ?",
            (status, batch_id)
        )

    inserted = Counter()

    # Create only missing stage records.
    updated_batches = [
        (batch[0], batch[1], batch[2], batch[3], assignment[batch[0]])
        for batch in batches
    ]

    for batch in updated_batches:
        add_missing_stage_records(batch, references, inserted)

    # Check the final distribution before committing.
    actual = dict(conn.execute("""
        SELECT status, COUNT(*)
        FROM Batch
        GROUP BY status
    """).fetchall())

    for status, expected in TARGET_COUNTS.items():
        if actual.get(status, 0) != expected:
            raise RuntimeError(
                f"Status check failed for {status}: "
                f"expected {expected}, got {actual.get(status, 0)}"
            )

    conn.commit()

    print("\nSUCCESS — status distribution:")
    for status, count in TARGET_COUNTS.items():
        print(f"  {status}: {count}")

    print("\nNewly inserted records:")
    for table, count in sorted(inserted.items()):
        print(f"  {table}: {count}")

    print("\nFinal table counts:")
    for table in [
        "Batch", "Collection_Record", "Processing_Record",
        "Storage_Record", "Transport_Log", "Retail_Inventory",
        "Inspection", "Risk_Score"
    ]:
        count = conn.execute(
            f'SELECT COUNT(*) FROM "{table}"'
        ).fetchone()[0]
        print(f"  {table}: {count}")

    print(f"\nBackup location: {BACKUP}")

except Exception:
    conn.rollback()
    print("\nERROR: changes rolled back. Your backup is at:", BACKUP)
    raise
finally:
    conn.close()