
import sqlite3

conn = sqlite3.connect("food_traceability.db")
conn.row_factory = sqlite3.Row

tables = [
    "Batch",
    "Farmer",
    "Collection_Center",
    "Collection_Record",
    "Processing_Plant",
    "Processing_Record",
    "Warehouse",
    "Storage_Record",
    "Transporter",
    "Transport_Log",
    "Retail_Store",
    "Retail_Inventory",
    "Inspection",
    "Risk_Score",
]

for table in tables:
    count = conn.execute(
        f'SELECT COUNT(*) FROM "{table}"'
    ).fetchone()[0]

    print(f"\n{'=' * 40}")
    print(f"{table}: {count} records")
    print("=" * 40)

    # Show existing reference records and a few batch examples.
    if table in [
        "Farmer", "Collection_Center", "Processing_Plant",
        "Warehouse", "Transporter", "Retail_Store", "Batch"
    ]:
        rows = conn.execute(
            f'SELECT * FROM "{table}" LIMIT 5'
        ).fetchall()

        for row in rows:
            print(dict(row))

# Show the valid status constraints, if defined in SQL.
print("\n=== Batch table definition ===")
definition = conn.execute("""
    SELECT sql
    FROM sqlite_master
    WHERE type = 'table' AND name = 'Batch'
""").fetchone()

print(definition["sql"] if definition else "Not found")

conn.close()
