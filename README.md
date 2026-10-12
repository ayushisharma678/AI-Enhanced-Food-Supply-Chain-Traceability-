# Food Supply Chain Traceability Dashboard

Beginner-friendly Streamlit dashboard for the DBS project. It reads the existing SQLite database and provides:

- Batch overview and search
- Recorded risk-label summary
- Farm-to-retail traceability details
- QR-code generation and PNG download

## 1. Open in VS Code

Extract this folder somewhere easy to find, then use VS Code → File → Open Folder and choose `Food_Traceability_Dashboard`.

## 2. Create a virtual environment

Open Terminal in VS Code (Terminal → New Terminal), then run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Run the app

```bash
streamlit run app.py
```

Streamlit should open the app in your browser, usually at `http://localhost:8501`.

## 4. Try the sample batch

Use `BATCH-2026-000123`. Select **Batch Traceability** to inspect the records, or **QR Code Generator** to download a QR image.

## Notes

- `food_traceability.db` is a copy of the database supplied in the project ZIP. This keeps the original download untouched.
- Existing risk values are read from `Risk_Score`; the app does not train or run a new model.
- A QR code using `localhost` opens on the same computer only. For phone scanning, use a reachable network/deployed URL and set `TRACEABILITY_BASE_URL` before starting the app.
- This is a student demonstration, not a food-safety certification system.
