import sqlite3
import shutil
from pathlib import Path
from datetime import date, datetime

DB = Path("food_traceability.db")

# Synthetic demo farmer records. Replace these with verified real data if needed.
DEMO_FARMERS = [
    ("R. Selvam", "Salem, Tamil Nadu"),
    ("Priya Kumar", "Erode, Tamil Nadu"),
    ("Arjun Patel", "Coimbatore, Tamil Nadu"),
    ("Meena Devi", "Madurai, Tamil Nadu"),
    ("Karthik Raj", "Tiruchirappalli, Tamil Nadu"),
    ("Lakshmi N", "Thanjavur, Tamil Nadu"),
    ("Vijay Anand", "Namakkal, Tamil Nadu"),
    ("Anitha R", "Dindigul, Tamil Nadu"),
    ("Suresh Babu", "Tirunelveli, Tamil Nadu"),
    ("Kavitha M", "Krishnagiri, Tamil Nadu"),
]

if not DB.exists():
    raise FileNotFoundError(
        f"Database not found: {DB.resolve()}\n"
        "Run this script from the folder containing food_traceability.db."
    )

# Always back up the database before changing it.
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = DB.with_name(f"food_traceability_backup_farmers_{stamp}.db")
shutil.copy2(DB, backup)
print(f"Backup created: {backup}")

conn = sqlite3.connect(DB)
conn.execute("PRAGMA foreign_keys = ON")

try:
    conn.execute("BEGIN")

    # Confirm expected columns exist.
    farmer_columns = {
        row[1] for row in conn.execute('PRAGMA table_info("Farmer")')
    }
    batch_columns = {
        row[1] for row in conn.execute('PRAGMA table_info("Batch")')
    }
    required_farmer = {"farmer_id", "name", "farm_location", "registered_on"}
    required_batch = {"batch_id", "farmer_id"}
    if not required_farmer.issubset(farmer_columns):
        raise RuntimeError(
            f"Farmer table columns differ from expected schema: {farmer_columns}"
        )
    if not required_batch.issubset(batch_columns):
        raise RuntimeError(
            f"Batch table columns differ from expected schema: {batch_columns}"
        )

    # Add demo farmers if they do not already exist. Keep existing farmer rows.
    farmer_ids = []
    for name, location in DEMO_FARMERS:
        row = conn.execute(
            "SELECT farmer_id FROM Farmer WHERE name = ? AND farm_location = ? LIMIT 1",
            (name, location),
        ).fetchone()

        if row:
            farmer_id = row[0]
        else:
            # contact_no may be NOT NULL in some versions of the schema.
            if "contact_no" in farmer_columns:
                conn.execute(
                    """INSERT INTO Farmer (name, contact_no, farm_location, registered_on)
                       VALUES (?, ?, ?, ?)""",
                    (name, "DEMO-NOT-A-REAL-CONTACT", location, date.today().isoformat()),
                )
            else:
                conn.execute(
                    """INSERT INTO Farmer (name, farm_location, registered_on)
                       VALUES (?, ?, ?)""",
                    (name, location, date.today().isoformat()),
                )
            farmer_id = conn.execute(
                "SELECT farmer_id FROM Farmer WHERE name = ? AND farm_location = ? "
                "ORDER BY farmer_id DESC LIMIT 1",
                (name, location),
            ).fetchone()[0]
        farmer_ids.append(farmer_id)

    batches = conn.execute(
        "SELECT batch_id FROM Batch ORDER BY batch_id"
    ).fetchall()
    if not batches:
        raise RuntimeError("No batches found in Batch table.")

    # Spread batches across demo farmers. Batch IDs and all journey records remain unchanged.
    for index, (batch_id,) in enumerate(batches):
        farmer_id = farmer_ids[index % len(farmer_ids)]
        conn.execute(
            "UPDATE Batch SET farmer_id = ? WHERE batch_id = ?",
            (farmer_id, batch_id),
        )

    # Verify the resulting assignment before commit.
    distinct_farmers = conn.execute(
        "SELECT COUNT(DISTINCT farmer_id) FROM Batch"
    ).fetchone()[0]
    missing_farmer = conn.execute(
        """SELECT COUNT(*) FROM Batch b
           LEFT JOIN Farmer f ON b.farmer_id = f.farmer_id
           WHERE f.farmer_id IS NULL"""
    ).fetchone()[0]

    if missing_farmer:
        raise RuntimeError(f"{missing_farmer} batch(es) have no valid farmer.")
    if len(batches) > 1 and distinct_farmers < 2:
        raise RuntimeError("Farmer assignment verification failed.")

    conn.commit()
    print(f"\nSUCCESS: assigned {len(batches)} batches across {distinct_farmers} farmers.")
    print("\nFarmer assignment summary:")
    rows = conn.execute(
        """SELECT f.name, f.farm_location, COUNT(b.batch_id)
           FROM Farmer f JOIN Batch b ON b.farmer_id = f.farmer_id
           GROUP BY f.farmer_id, f.name, f.farm_location
           ORDER BY f.name"""
    ).fetchall()
    for name, location, count in rows:
        print(f"  {name} — {location}: {count} batch(es)")

    print("\nImportant: these are synthetic demo farmer details, not verified real people.")
    print("Backup:", backup)

except Exception:
    conn.rollback()
    print("\nERROR: changes rolled back. Original database backup:", backup)
    raise
finally:
    conn.close()
