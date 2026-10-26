
import sqlite3
import random
import json
from datetime import date, timedelta
from pathlib import Path

# Use the database beside this script.
DB_PATH = Path(__file__).resolve().parent / "food_traceability.db"

random.seed(42)

crops = [
    "Rice", "Tomato", "Leafy_Greens", "Wheat",
    "Poultry", "Milk", "Onion", "Potato"
]

stages = [
    "Harvested",
    "Processing",
    "Stored",
    "In_Transit",
    "Delivered",
    "Retail",
    "Sold",
    "Recalled"
]

# Illustrative labels for a demo dashboard, NOT actual predictions.
risk_examples = [
    (0.08, "Low"),
    (0.18, "Low"),
    (0.27, "Low"),
    (0.42, "Medium"),
    (0.55, "Medium"),
    (0.68, "High"),
    (0.82, "High"),
    (0.35, "Medium"),
    (0.12, "Low"),
    (0.73, "High"),
]

def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = sqlite3.connect(DB_PATH)

    try:
        conn.execute("PRAGMA foreign_keys = ON")

        # Inspect the existing database structure.
        batch_columns = {
            row[1]: row
            for row in conn.execute(
                "PRAGMA table_info(Batch)"
            )
        }
        farmer_columns = {
            row[1]: row
            for row in conn.execute(
                "PRAGMA table_info(Farmer)"
            )
        }
        risk_columns = {
            row[1]: row
            for row in conn.execute(
                "PRAGMA table_info(Risk_Score)"
            )
        }

        required_batch = {
            "batch_id", "crop_type", "harvest_date",
            "quantity_kg", "status", "farmer_id"
        }
        if not required_batch.issubset(batch_columns):
            raise RuntimeError(
                "Batch schema differs from expected columns. "
                f"Found: {list(batch_columns)}"
            )

        if "farmer_id" not in farmer_columns:
            raise RuntimeError(
                "Could not find Farmer.farmer_id."
            )

        required_risk = {
            "batch_id", "model_version", "predicted_risk",
            "risk_level", "scored_on", "top_features"
        }
        if not required_risk.issubset(risk_columns):
            raise RuntimeError(
                "Risk_Score schema differs from expected columns. "
                f"Found: {list(risk_columns)}"
            )

        farmer = conn.execute(
            "SELECT farmer_id FROM Farmer LIMIT 1"
        ).fetchone()

        if farmer is None:
            raise RuntimeError(
                "No farmer exists. Add a farmer before "
                "creating batches."
            )

        farmer_id = farmer[0]

        existing = {
            row[0] for row in conn.execute(
                "SELECT batch_id FROM Batch"
            )
        }

        inserted = 0
        today = date.today()

        # Generate 50 new, uniquely identified batches.
        with conn:
            for i in range(1, 51):
                batch_id = f"BATCH-DEMO-{i:04d}"

                # Do not duplicate batches if rerun.
                if batch_id in existing:
                    continue

                crop = crops[(i - 1) % len(crops)]
                stage = stages[(i - 1) % len(stages)]
                harvest_date = (
                    today - timedelta(days=random.randint(1, 45))
                ).isoformat()
                quantity = random.randrange(100, 2001, 50)

                conn.execute(
                    """
                    INSERT INTO Batch
                    (batch_id, crop_type, harvest_date,
                     quantity_kg, status, farmer_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        batch_id, crop, harvest_date,
                        quantity, stage, farmer_id
                    )
                )

                probability, risk_level = risk_examples[
                    (i - 1) % len(risk_examples)
                ]

                details = {
                    "note": (
                        "Synthetic demonstration score; "
                        "not a real food-safety prediction."
                    )
                }

                conn.execute(
                    """
                    INSERT INTO Risk_Score
                    (batch_id, model_version, predicted_risk,
                     risk_level, scored_on, top_features)
                    VALUES (?, ?, ?, ?, datetime('now'), ?)
                    """,
                    (
                        batch_id,
                        "DEMO-SYNTHETIC-NOT-A-PREDICTION",
                        probability,
                        risk_level,
                        json.dumps(details)
                    )
                )

                inserted += 1

        total = conn.execute(
            "SELECT COUNT(*) FROM Batch"
        ).fetchone()[0]

        print(f"New demo batches added: {inserted}")
        print(f"Total batches in database: {total}")
        print("Demo risk labels added for dashboard testing.")
        print(
            "Scores are synthetic; no model prediction "
            "was performed."
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()
