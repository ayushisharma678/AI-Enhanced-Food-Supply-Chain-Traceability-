# Food Supply Chain Traceability Dashboard

Streamlit dashboard for the DBS project, *AI-Enhanced Food Supply Chain Traceability and Contamination Risk Scoring*. It reads a SQLite database and provides:

- Batch overview and search
- Recorded risk-label summary
- Farm-to-retail traceability details for each batch
- QR-code generation and PNG download
- AI risk prediction (Random Forest) for an existing batch or a new-conditions scenario. Predictions for existing batches are appended to `Risk_Score`.

> **Important:** the model is trained on **synthetic** data, and many demo batches use placeholder inputs. Scores are for demonstration only and are not food-safety verdicts.

## 1. Setup

Open the project folder in VS Code, then in a terminal run:

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Keep `scikit-learn` at the version in `requirements.txt`. The saved model was created with it, and results can change with other versions.

## 2. Run the app

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

Try the sample batch `BATCH-2026-000123`:

- **Batch Traceability** shows the records for each stage.
- **QR Code Generator** creates a downloadable QR image.
- **AI Risk Prediction** scores the batch and saves the result to `Risk_Score`.

## 3. QR codes on a phone

A QR code that points to `localhost` opens only on the same computer. To scan with a phone, set a reachable address before starting the app:

```bash
export TRACEABILITY_BASE_URL="http://<your-computer-ip>:8501"
streamlit run app.py
```

If the variable is not set, `app.py` falls back to a hard-coded address (`http://10.57.22.107:8501/`), which will not work on other networks.

## 4. Reproduce the paper's numbers

The numbers in the paper's Table II, Table III and Fig. 2 come from `fair_evaluation.py`.

```bash
python fair_evaluation.py
```

It reads `synthetic_batches.csv` and writes `fair_results.json`. It takes one to two minutes. The protocol is:

- Logistic regression, Random Forest and Gradient Boosting use the same class-balanced weighting. No hyperparameters are tuned.
- The 80/20 stratified split uses `random_state=42`, giving 6,400 training and 1,600 test records (181 contaminated).
- Each model's threshold is chosen from 5-fold cross-validation on the training split only: the highest threshold with out-of-fold recall of at least 80%.
- The test split is used once. Intervals are 95% bootstrap intervals over 2,000 resamples.
- Feature importance is permutation importance (drop in test ROC-AUC).

`fair_evaluation.py` refits the Random Forest. It matches the shipped `food_risk_model.joblib` to within about 0.1 percentage point of ROC-AUC, so recall at the same threshold can differ by under one point. `evaluate_models.py`, which scores the shipped model, reports 85.1% recall at threshold 0.3. The paper reports 84.5% from the refit.

## 5. Files

**Application and model**

- `app.py`: Streamlit dashboard.
- `food_traceability.db`: SQLite database (15 tables, 51 batches).
- `food_risk_model.joblib`: trained Random Forest used by the app.
- `train_model.py`: trains the Random Forest and writes `food_risk_model.joblib` and `trained_model_metrics.json`.
- `synthetic_batches.csv`: 8,000 synthetic batch records used for training and evaluation. The script that generated it is not included.

**Evaluation**

- `fair_evaluation.py`: protocol above; writes `fair_results.json`. Source of the paper's results tables.
- `evaluate_models.py`: earlier comparison at fixed thresholds 0.5 and 0.3 on the shipped model; writes `model_results.json` and `model_comparison_chart.png`. Not used for the paper's tables.

**Database**

- `schema.sql` / `seed.sql`: the 14 core tables and the sample batch.
- `AI_Demo_Input`: a 15th table created by `complete_batch_data.py`. It holds labelled synthetic placeholder inputs, used only when a recorded value is missing.

**Helper scripts** (each makes a backup copy of the database before changing it)

- `add_sample_batches.py`: adds 50 demonstration batches with placeholder risk labels.
- `update_tracibility.py`: adds illustrative stage records so batches match their status.
- `update_farmers.py`: adds ten synthetic farmers and spreads batches across them.
- `complete_batch_data.py`: creates and fills `AI_Demo_Input`.
- `check_database.py`, `inspect_records.py`: print table structure and sample rows.

## 6. Notes and limitations

- The *Dashboard* and *Batch Traceability* pages show scores already stored in `Risk_Score`. The *AI Risk Prediction* page scores a batch and appends a new row. History is kept.
- Of the 53 stored scores, 50 are placeholder labels (model version `DEMO-SYNTHETIC-NOT-A-PREDICTION`) added to populate the dashboard.
- The prediction page flags a class at the model's default threshold of 0.5 and shows illustrative bands at 0.30 and 0.60. The paper's recall-oriented operating point for the Random Forest is 0.30.
- Most demo storage and transport records use the same values (5.0 °C, 65% humidity, 8.0 °C), so they carry little information.
- Records are added through scripts. There are no data-entry forms, authentication or tamper protection.
- This is a student demonstration, not a food-safety certification system.
