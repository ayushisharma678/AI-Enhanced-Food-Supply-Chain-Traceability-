# Food Supply Chain Traceability Dashboard

Streamlit dashboard for the DBS project (AI-enhanced food supply chain traceability). It reads the SQLite database and provides:

- Batch overview and search
- Recorded risk-label summary
- Farm-to-retail traceability details
- QR-code generation and PNG download
- AI risk prediction (Random Forest) for an existing batch or a new-conditions scenario; predictions for existing batches are saved to `Risk_Score`

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

## Files

- `schema.sql` / `seed.sql` - database schema (14 tables) and the sample batch; `food_traceability.db` is built from them.
- `train_model.py` - trains the Random Forest and writes `food_risk_model.joblib` and `trained_model_metrics.json`.
- `evaluate_models.py` - compares Logistic Regression, Random Forest and Gradient Boosting at thresholds 0.5 and 0.3 and writes `model_results.json` and `model_comparison_chart.png` (these are the numbers used in the paper).
- Keep `scikit-learn` at the version in `requirements.txt`; the saved model was created with it, and results can change with other versions.

## Notes

- The *Dashboard* and *Batch Traceability* pages show risk values already stored in `Risk_Score`. The *AI Risk Prediction* page loads `food_risk_model.joblib`, scores a batch from its database records, and appends the result to `Risk_Score` (history is kept, nothing is overwritten).
- The model is trained on **synthetic** data (`synthetic_batches.csv`), so its scores are not real food-safety verdicts.
- A QR code using `localhost` opens on the same computer only. For phone scanning, use a reachable network/deployed URL and set `TRACEABILITY_BASE_URL` before starting the app.
- This is a student demonstration, not a food-safety certification system.
