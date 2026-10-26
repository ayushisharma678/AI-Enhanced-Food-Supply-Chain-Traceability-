
import sqlite3

conn = sqlite3.connect("food_traceability.db")
conn.execute("PRAGMA foreign_keys")

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
    print(f"\n{'=' * 45}")
    print(f"TABLE: {table}")
    print("=" * 45)

    columns = conn.execute(
        f'PRAGMA table_info("{table}")'
    ).fetchall()

    for col in columns:
        print(f"Column: {col[1]} | Type: {col[2]} | "
              f"Primary key: {col[5]}")

    foreign_keys = conn.execute(
        f'PRAGMA foreign_key_list("{table}")'
    ).fetchall()

    for fk in foreign_keys:
        print(f"Foreign key: {fk[3]} -> {fk[2]}.{fk[4]}")

conn.close()
