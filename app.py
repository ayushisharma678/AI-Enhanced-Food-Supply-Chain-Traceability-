from pathlib import Path
import os
import json
import sqlite3
from datetime import datetime
from io import BytesIO

import pandas as pd
import qrcode
import streamlit as st
import joblib

APP_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("FOOD_TRACEABILITY_DB", str(APP_DIR / "food_traceability.db")))

st.set_page_config(
    page_title="Food Supply Chain Traceability",
    page_icon="🥬",
    layout="wide",
)


def get_connection():
    if not DB_PATH.exists():
        st.error(f"Database not found: {DB_PATH}. Put food_traceability.db beside app.py.")
        st.stop()
    return sqlite3.connect(str(DB_PATH))


def read_sql(query, params=()):
    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


def get_batches(search=""):
    query = """
        SELECT
            b.batch_id,
            b.crop_type,
            b.harvest_date,
            b.quantity_kg,
            b.status,
            f.name AS farmer_name,
            f.farm_location,
            rs.predicted_risk,
            rs.risk_level,
            rs.scored_on,
            rs.model_version
        FROM Batch b
        LEFT JOIN Farmer f ON f.farmer_id = b.farmer_id
        LEFT JOIN Risk_Score rs ON rs.score_id = (
            SELECT rs2.score_id
            FROM Risk_Score rs2
            WHERE rs2.batch_id = b.batch_id
            ORDER BY rs2.scored_on DESC, rs2.score_id DESC
            LIMIT 1
        )
        WHERE (? = '' OR lower(b.batch_id) LIKE lower(?) OR lower(b.crop_type) LIKE lower(?)
               OR lower(COALESCE(f.name, '')) LIKE lower(?))
        ORDER BY b.harvest_date DESC, b.batch_id
    """
    pattern = f"%{search}%"
    return read_sql(query, (search, pattern, pattern, pattern))


def get_traceability(batch_id):
    batch = read_sql("""
        SELECT b.*, f.name AS farmer_name, f.farm_location, f.contact_no AS farmer_contact
        FROM Batch b LEFT JOIN Farmer f ON f.farmer_id = b.farmer_id
        WHERE b.batch_id = ?
    """, (batch_id,))
    if batch.empty:
        return None

    data = {"batch": batch.iloc[0].to_dict()}
    data["collection"] = read_sql("""
        SELECT cr.received_date, cr.grade, cc.name AS collection_center, cc.location
        FROM Collection_Record cr LEFT JOIN Collection_Center cc ON cc.center_id = cr.center_id
        WHERE cr.batch_id = ? ORDER BY cr.received_date
    """, (batch_id,))
    data["processing"] = read_sql("""
        SELECT pr.process_date, pr.process_type, pr.output_qty_kg,
               pp.name AS processing_plant, pp.location, pp.license_no
        FROM Processing_Record pr LEFT JOIN Processing_Plant pp ON pp.plant_id = pr.plant_id
        WHERE pr.batch_id = ? ORDER BY pr.process_date
    """, (batch_id,))
    data["storage"] = read_sql("""
        SELECT sr.in_date, sr.out_date, sr.temperature_c, sr.humidity_pct,
               w.name AS warehouse, w.location
        FROM Storage_Record sr LEFT JOIN Warehouse w ON w.warehouse_id = sr.warehouse_id
        WHERE sr.batch_id = ? ORDER BY sr.in_date
    """, (batch_id,))
    data["transport"] = read_sql("""
        SELECT tl.origin, tl.destination, tl.dispatch_time, tl.arrival_time, tl.transit_temp_c,
               t.name AS transporter, t.vehicle_no
        FROM Transport_Log tl LEFT JOIN Transporter t ON t.transporter_id = tl.transporter_id
        WHERE tl.batch_id = ? ORDER BY tl.dispatch_time
    """, (batch_id,))
    data["retail"] = read_sql("""
        SELECT ri.received_date, ri.quantity_kg, ri.unit_price,
               rs.name AS retail_store, rs.location
        FROM Retail_Inventory ri LEFT JOIN Retail_Store rs ON rs.store_id = ri.store_id
        WHERE ri.batch_id = ? ORDER BY ri.received_date
    """, (batch_id,))
    data["inspections"] = read_sql("""
        SELECT stage, inspector_name, inspection_date, result, contamination_type, notes
        FROM Inspection WHERE batch_id = ? ORDER BY inspection_date
    """, (batch_id,))
    data["risks"] = read_sql("""
        SELECT model_version, predicted_risk, risk_level, scored_on, top_features
        FROM Risk_Score WHERE batch_id = ? ORDER BY scored_on DESC, score_id DESC
    """, (batch_id,))
    return data


@st.cache_resource
def load_risk_model():
    model_path = APP_DIR / "food_risk_model.joblib"
    if not model_path.exists():
        return None
    return joblib.load(model_path)


def make_qr(url):
    image = qrcode.make(url)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def show_records(title, df):
    st.markdown(f"#### {title}")
    if df is None or df.empty:
        st.caption("No record has been entered for this stage yet.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


def render_traceability(batch_id, consumer_view=False):
    trace = get_traceability(batch_id)
    if trace is None:
        st.error(f"No batch found with ID: {batch_id}")
        st.info("Check the batch ID or choose a batch from the dashboard.")
        return

    b = trace["batch"]
    st.title(f"🥬 Traceability: {b['batch_id']}")
    st.caption("Batch journey from farm to retail, based on records stored in the project database.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Crop", str(b.get("crop_type") or "—"))
    c2.metric("Quantity", f"{b.get('quantity_kg') or 0:,.0f} kg")
    c3.metric("Current status", str(b.get("status") or "Unknown"))
    risk = trace["risks"]
    if not risk.empty and pd.notna(risk.iloc[0].get("predicted_risk")):
        risk_pct = float(risk.iloc[0]["predicted_risk"]) * 100
        c4.metric("Recorded risk score", f"{risk_pct:.1f}%", str(risk.iloc[0].get("risk_level") or "Unlabelled"))
    else:
        c4.metric("Recorded risk score", "Not available")

    if consumer_view:
        st.info("This page displays recorded traceability information. A low model risk score is not a guarantee that food is safe to consume.")

    st.markdown("### 1. Farm origin")
    st.write(f"**Farmer:** {b.get('farmer_name') or 'Not recorded'}")
    st.write(f"**Farm location:** {b.get('farm_location') or 'Not recorded'}")
    st.write(f"**Harvest date:** {b.get('harvest_date') or 'Not recorded'}")

    show_records("2. Collection", trace["collection"])
    show_records("3. Processing", trace["processing"])
    show_records("4. Storage conditions", trace["storage"])
    show_records("5. Transportation", trace["transport"])
    show_records("6. Retail", trace["retail"])
    show_records("7. Inspection records", trace["inspections"])
    show_records("8. Risk assessment history", trace["risks"])

    with st.expander("What do these results mean?"):
        st.write("The risk score and risk level above are read from the existing Risk_Score table. They are not recalculated by this dashboard. Missing records mean that information has not been entered in the database; they do not prove that a stage did not occur.")


MODEL_CROP_TYPES = ["Rice", "Tomato", "Leafy_Greens", "Wheat", "Poultry", "Milk", "Onion", "Potato"]
MODEL_STAGES = ["Collection", "Retail", "Storage", "Processing", "Transport"]


def _parse_datetime(value):
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    try:
        return pd.to_datetime(value)
    except Exception:
        return None


def get_batch_prediction_inputs(batch_id):
    """Build model inputs from recorded batch data; explicitly flag any fallback values."""
    batch_df = read_sql(
        "SELECT batch_id, crop_type, harvest_date, status FROM Batch WHERE batch_id = ?",
        (batch_id,),
    )
    if batch_df.empty:
        return None, ["Batch record not found."]
    batch = batch_df.iloc[0]
    notes = []

    # Crop type must match a category seen during model training.
    crop_raw = str(batch.get("crop_type") or "").strip()
    crop_lookup = {value.lower(): value for value in MODEL_CROP_TYPES}
    crop_type = crop_lookup.get(crop_raw.lower())
    if crop_type is None:
        notes.append(f"Crop '{crop_raw or 'unknown'}' is not a category supported by the trained model. Choose a supported crop in New conditions mode.")

    storage = read_sql(
        "SELECT in_date, out_date, temperature_c, humidity_pct FROM Storage_Record WHERE batch_id = ? ORDER BY in_date DESC LIMIT 1",
        (batch_id,),
    )
    transport = read_sql(
        "SELECT dispatch_time, arrival_time, transit_temp_c FROM Transport_Log WHERE batch_id = ? ORDER BY dispatch_time DESC LIMIT 1",
        (batch_id,),
    )
    inspections = read_sql(
        "SELECT result, contamination_type FROM Inspection WHERE batch_id = ?",
        (batch_id,),
    )
    collection = read_sql(
        "SELECT received_date FROM Collection_Record WHERE batch_id = ? ORDER BY received_date DESC LIMIT 1",
        (batch_id,),
    )
    processing = read_sql(
        "SELECT process_date FROM Processing_Record WHERE batch_id = ? ORDER BY process_date DESC LIMIT 1",
        (batch_id,),
    )
    retail = read_sql(
        "SELECT received_date FROM Retail_Inventory WHERE batch_id = ? ORDER BY received_date DESC LIMIT 1",
        (batch_id,),
    )

    status = str(batch.get("status") or "").strip().lower()
    status_map = {
        "collection": "Collection", "collected": "Collection",
        "processing": "Processing", "processed": "Processing",
        "storage": "Storage", "stored": "Storage",
        "transport": "Transport", "in transit": "Transport", "transit": "Transport",
        "retail": "Retail", "sold": "Retail",
    }
    stage = status_map.get(status)
    if stage is None:
        # Infer the latest documented stage if Batch.status doesn't match training labels.
        if not retail.empty:
            stage = "Retail"
        elif not transport.empty:
            stage = "Transport"
        elif not storage.empty:
            stage = "Storage"
        elif not processing.empty:
            stage = "Processing"
        elif not collection.empty:
            stage = "Collection"
        else:
            stage = "Collection"
        notes.append(f"Batch status '{batch.get('status') or 'missing'}' did not match a model stage; inferred '{stage}' from available records.")

    storage_temp = 5.9
    humidity = 75.0
    storage_duration = 24.0
    if not storage.empty:
        row = storage.iloc[0]
        if pd.notna(row.get("temperature_c")):
            storage_temp = float(row["temperature_c"])
        else:
            notes.append("Storage temperature is missing; used demonstration fallback 5.9°C.")
        if pd.notna(row.get("humidity_pct")):
            humidity = float(row["humidity_pct"])
        else:
            notes.append("Humidity is missing; used demonstration fallback 75%.")
        start = _parse_datetime(row.get("in_date"))
        end = _parse_datetime(row.get("out_date"))
        if start is not None and end is not None and end >= start:
            storage_duration = max(0.0, (end - start).total_seconds() / 3600)
        else:
            notes.append("Storage duration could not be calculated from in/out dates; used demonstration fallback 24 hours.")
    else:
        notes.append("No storage record found; used demonstration fallbacks for storage temperature, humidity and duration.")

    transit_time = 4.0
    transit_temp = 8.0
    if not transport.empty:
        row = transport.iloc[0]
        if pd.notna(row.get("transit_temp_c")):
            transit_temp = float(row["transit_temp_c"])
        else:
            notes.append("Transit temperature is missing; used demonstration fallback 8°C.")
        start = _parse_datetime(row.get("dispatch_time"))
        end = _parse_datetime(row.get("arrival_time"))
        if start is not None and end is not None and end >= start:
            transit_time = max(0.0, (end - start).total_seconds() / 3600)
        else:
            notes.append("Transit duration could not be calculated from dispatch/arrival times; used demonstration fallback 4 hours.")
    else:
        notes.append("No transport record found; used demonstration fallbacks for transit time and temperature.")

    prior_failures = 0
    if not inspections.empty:
        results = inspections["result"].fillna("").astype(str).str.strip().str.lower()
        prior_failures = int(results.isin(["fail", "failed", "reject", "rejected"] ).sum())

    # Use the latest recorded supply-chain event as the reference point for age.
    harvest = _parse_datetime(batch.get("harvest_date"))
    event_values = []
    for frame, column in [(collection, "received_date"), (processing, "process_date"),
                          (storage, "out_date"), (transport, "arrival_time"),
                          (retail, "received_date")]:
        if not frame.empty:
            dt = _parse_datetime(frame.iloc[0].get(column))
            if dt is not None:
                event_values.append(dt)
    reference = max(event_values) if event_values else harvest
    days_since_harvest = 1.0
    if harvest is not None and reference is not None and reference >= harvest:
        days_since_harvest = max(0.0, (reference - harvest).total_seconds() / 86400)
    else:
        notes.append("Days since harvest could not be calculated; used demonstration fallback 1 day.")

    values = {
        "crop_type": crop_type,
        "supply_chain_stage": stage,
        "storage_temp_c": float(storage_temp),
        "storage_duration_hrs": float(storage_duration),
        "transit_time_hrs": float(transit_time),
        "transit_temp_c": float(transit_temp),
        "humidity_pct": float(humidity),
        "prior_inspection_fail_count": int(prior_failures),
        "days_since_harvest": float(days_since_harvest),
    }
    return values, notes


def run_risk_prediction(risk_model, values):
    input_df = pd.DataFrame([values])
    classes = list(risk_model.classes_)
    if 1 not in classes:
        raise ValueError("The loaded model does not contain contamination class 1.")
    probability = float(risk_model.predict_proba(input_df)[0][classes.index(1)])
    predicted_class = int(risk_model.predict(input_df)[0])
    return input_df, probability, predicted_class


def get_top_model_features(risk_model, limit=3):
    """Return the model's globally most important features, when available."""
    try:
        preprocessor = risk_model.named_steps["preprocessor"]
        classifier = risk_model.named_steps["classifier"]
        names = list(preprocessor.get_feature_names_out())
        importances = list(classifier.feature_importances_)
        ranked = sorted(zip(names, importances), key=lambda item: item[1], reverse=True)
        return [{"feature": name, "importance": round(float(score), 6)}
                for name, score in ranked[:limit]]
    except Exception:
        return []


def save_risk_score(batch_id, probability, risk_model, input_values):
    """Append a new model score to Risk_Score without overwriting history."""
    if probability < 0.30:
        risk_level = "Low"
    elif probability < 0.60:
        risk_level = "Medium"
    else:
        risk_level = "High"

    model_version = "RandomForest-synthetic-v1"
    scored_on = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    details = {
        "top_model_features": get_top_model_features(risk_model),
        "input_values": input_values,
        "note": "Feature importance is global to the trained model; probability bands are illustrative.",
    }
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO Risk_Score
               (batch_id, model_version, predicted_risk, risk_level, scored_on, top_features)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (batch_id, model_version, float(probability), risk_level,
             scored_on, json.dumps(details, ensure_ascii=False)),
        )
    return risk_level, scored_on


# A QR can open this app with ?batch_id=BATCH-... in the URL.
query_batch = st.query_params.get("batch_id", "")
if isinstance(query_batch, list):
    query_batch = query_batch[0] if query_batch else ""

st.sidebar.title("🥬 Food Traceability")
st.sidebar.caption("DBS project demonstration")
if query_batch:
    page = "Batch Traceability"
    st.sidebar.success("Opened from a batch QR link")
else:
    page = st.sidebar.radio("Navigate", ["Dashboard", "Batch Traceability", "QR Code Generator", "AI Risk Prediction"])

if page == "Dashboard":
    st.title("Food Supply Chain Dashboard")
    st.caption("Batch monitoring, traceability and recorded contamination-risk indicators.")
    batches = get_batches()
    if batches.empty:
        st.warning("No batches found in the database yet.")
        st.stop()

    total_batches = len(batches)
    total_qty = pd.to_numeric(batches["quantity_kg"], errors="coerce").fillna(0).sum()
    high_risk = batches["risk_level"].fillna("").str.lower().isin(["high", "critical"]).sum()
    missing_risk = batches["risk_level"].isna().sum()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total batches", f"{total_batches:,}")
    m2.metric("Recorded quantity", f"{total_qty:,.0f} kg")
    m3.metric("High / critical risk labels", int(high_risk))
    m4.metric("Without risk label", int(missing_risk))

    st.markdown("### Batch records")
    search = st.text_input("Search by batch ID, crop, or farmer", placeholder="e.g. BATCH-2026-000123")
    filtered = get_batches(search.strip())
    display = filtered.copy()
    if "predicted_risk" in display:
        display["predicted_risk"] = display["predicted_risk"].apply(
            lambda x: f"{float(x)*100:.1f}%" if pd.notna(x) else "Not scored"
        )
    display = display.rename(columns={
        "batch_id": "Batch ID", "crop_type": "Crop", "harvest_date": "Harvest date",
        "quantity_kg": "Quantity (kg)", "status": "Status", "farmer_name": "Farmer",
        "farm_location": "Farm location", "predicted_risk": "Risk score",
        "risk_level": "Risk level", "scored_on": "Last scored", "model_version": "Model version"
    })
    st.dataframe(display, use_container_width=True, hide_index=True)

    if not filtered.empty:
        chosen = st.selectbox("Open a batch", filtered["batch_id"].tolist())
        if st.button("View full traceability", type="primary"):
            st.query_params["batch_id"] = chosen
            st.rerun()

    st.markdown("### Risk-label summary")
    risk_counts = batches["risk_level"].fillna("Not scored").value_counts().rename_axis("Risk level").reset_index(name="Batch count")
    st.bar_chart(risk_counts.set_index("Risk level"))
    st.caption("Risk labels are taken from the database; this chart does not create new predictions.")

elif page == "Batch Traceability":
    if query_batch:
        render_traceability(str(query_batch), consumer_view=True)
    else:
        batches = get_batches()
        if batches.empty:
            st.warning("No batches found in the database.")
        else:
            selected = st.selectbox("Select a batch ID", batches["batch_id"].tolist())
            render_traceability(selected, consumer_view=True)

elif page == "QR Code Generator":
    st.title("QR Code Generator")
    st.write("Generate a QR code for a batch's traceability page.")
    batches = get_batches()
    if batches.empty:
        st.warning("No batches are available to generate a QR code.")
    else:
        selected = st.selectbox("Choose batch", batches["batch_id"].tolist())
        base_url = os.getenv("TRACEABILITY_BASE_URL", "http://172.17.107.195:8503/").rstrip("/")
        trace_url = f"{base_url}/?batch_id={selected}"
        st.code(trace_url, language="text")
        st.image(make_qr(trace_url), caption=f"QR code for {selected}", width=240)
        st.download_button(
            "Download QR code (PNG)",
            data=make_qr(trace_url),
            file_name=f"{selected}_QR.png",
            mime="image/png",
        )
        st.warning("Local-demo note: localhost QR links work on the same computer. To scan with a phone, the app must be reachable from that phone (for example, using your Mac's local network IP on the same Wi-Fi, or deploying the app online).")

elif page == "AI Risk Prediction":
    st.title("AI Contamination-Risk Prediction")
    st.caption("Use recorded conditions from an existing batch or enter conditions for a new scenario.")
    st.warning(
        "This model was trained on synthetic data. Its output is for project demonstration, "
        "not a certified food-safety assessment. A low score does not prove food is safe."
    )

    try:
        risk_model = load_risk_model()
    except Exception as exc:
        risk_model = None
        st.error(f"Could not load food_risk_model.joblib: {exc}")

    if risk_model is None:
        st.info(
            "Model file not found. Run `python train_model.py` in the project terminal "
            "and make sure food_risk_model.joblib is beside app.py."
        )
    else:
        prediction_mode = st.radio(
            "Choose prediction mode",
            ["Existing batch", "New conditions"],
            horizontal=True,
            help="Existing batch mode reads recorded values where available. New conditions mode lets you enter a separate scenario.",
        )
        prediction_values = None
        prediction_label = ""
        prediction_notes = []
        prediction_batch_id = None
        submitted = False

        if prediction_mode == "Existing batch":
            batches = get_batches()
            if batches.empty:
                st.warning("No batch records are available. Choose New conditions mode instead.")
            else:
                selected_batch = st.selectbox(
                    "Select an existing batch",
                    batches["batch_id"].astype(str).tolist(),
                    key="existing_prediction_batch",
                )
                values, notes = get_batch_prediction_inputs(selected_batch)
                prediction_notes = notes
                if values and values.get("crop_type") is not None:
                    st.markdown("#### Conditions assembled from the database")
                    st.caption("Values are derived from stored records where possible. Any fallback values are listed below.")
                    source_df = pd.DataFrame([
                        {"Model input": "Crop type", "Value": values["crop_type"], "Source": "Batch.crop_type"},
                        {"Model input": "Supply-chain stage", "Value": values["supply_chain_stage"], "Source": "Batch.status / recorded journey"},
                        {"Model input": "Storage temperature (°C)", "Value": values["storage_temp_c"], "Source": "Latest Storage_Record"},
                        {"Model input": "Storage duration (hours)", "Value": round(values["storage_duration_hrs"], 2), "Source": "Storage_Record in/out dates"},
                        {"Model input": "Transit time (hours)", "Value": round(values["transit_time_hrs"], 2), "Source": "Transport_Log dispatch/arrival times"},
                        {"Model input": "Transit temperature (°C)", "Value": values["transit_temp_c"], "Source": "Latest Transport_Log"},
                        {"Model input": "Humidity (%)", "Value": values["humidity_pct"], "Source": "Latest Storage_Record"},
                        {"Model input": "Previous inspection failures", "Value": values["prior_inspection_fail_count"], "Source": "Inspection results marked Fail/Reject"},
                        {"Model input": "Days since harvest", "Value": round(values["days_since_harvest"], 2), "Source": "Harvest date to latest recorded event"},
                    ])
                    st.dataframe(source_df, use_container_width=True, hide_index=True)
                    for note in prediction_notes:
                        st.warning(note)
                    if st.button("Predict and save risk for selected batch", type="primary", key="predict_existing_batch"):
                        prediction_values = values
                        prediction_label = f"Existing batch: {selected_batch}"
                        prediction_batch_id = selected_batch
                        submitted = True
                elif values:
                    st.error("The batch crop type is not supported by this trained model. Use New conditions mode and select a supported crop category.")
                    for note in prediction_notes:
                        st.warning(note)

        else:
            st.markdown("### Enter new batch conditions")
            st.caption("This scenario is not saved as a batch or written to the database.")
            with st.form("new_risk_prediction_form"):
                c1, c2 = st.columns(2)
                with c1:
                    crop_type = st.selectbox("Crop type", MODEL_CROP_TYPES, index=1, key="new_crop_type")
                    supply_chain_stage = st.selectbox("Supply-chain stage", MODEL_STAGES, index=0, key="new_supply_chain_stage")
                    storage_temp_c = st.number_input("Storage temperature (°C)", value=5.9, step=0.5, key="new_storage_temp")
                    storage_duration_hrs = st.number_input("Storage duration (hours)", min_value=0.0, value=24.0, step=1.0, key="new_storage_duration")
                with c2:
                    transit_time_hrs = st.number_input("Transit time (hours)", min_value=0.0, value=4.0, step=0.5, key="new_transit_time")
                    transit_temp_c = st.number_input("Transit temperature (°C)", value=8.0, step=0.5, key="new_transit_temp")
                    humidity_pct = st.number_input("Humidity (%)", min_value=0.0, max_value=100.0, value=75.0, step=1.0, key="new_humidity")
                    prior_inspection_fail_count = st.number_input("Previous inspection failures", min_value=0, value=0, step=1, key="new_inspection_failures")
                    days_since_harvest = st.number_input("Days since harvest", min_value=0.0, value=1.0, step=0.5, key="new_days_since_harvest")
                new_submitted = st.form_submit_button("Predict new scenario", type="primary")
            if new_submitted:
                prediction_values = {
                    "crop_type": crop_type,
                    "supply_chain_stage": supply_chain_stage,
                    "storage_temp_c": float(storage_temp_c),
                    "storage_duration_hrs": float(storage_duration_hrs),
                    "transit_time_hrs": float(transit_time_hrs),
                    "transit_temp_c": float(transit_temp_c),
                    "humidity_pct": float(humidity_pct),
                    "prior_inspection_fail_count": int(prior_inspection_fail_count),
                    "days_since_harvest": float(days_since_harvest),
                }
                prediction_label = "New conditions scenario"
                submitted = True

        if submitted and prediction_values:
            try:
                input_df, probability, predicted_class = run_risk_prediction(risk_model, prediction_values)
                st.markdown("### Prediction result")
                st.caption(prediction_label)
                m1, m2 = st.columns(2)
                m1.metric("Model-estimated contamination probability", f"{probability * 100:.1f}%")
                m2.metric("Predicted class", "Contamination class (1)" if predicted_class == 1 else "Non-contamination class (0)")
                st.progress(max(0.0, min(1.0, probability)))
                if probability < 0.30:
                    st.info("Demo band: Lower estimated probability")
                elif probability < 0.60:
                    st.warning("Demo band: Moderate estimated probability")
                else:
                    st.error("Demo band: Higher estimated probability")
                st.caption("The probability and display bands are for demonstration only. The 30% and 60% bands are illustrative thresholds, not validated safety limits.")
                if prediction_batch_id:
                    try:
                        saved_level, saved_time = save_risk_score(
                            prediction_batch_id, probability, risk_model, prediction_values
                        )
                        st.success(
                            f"Prediction saved to Risk_Score for {prediction_batch_id}. "
                            f"Recorded level: {saved_level}; time: {saved_time}. "
                            "The dashboard and traceability history will use this latest saved score."
                        )
                    except Exception as save_exc:
                        st.error(f"Prediction was calculated but could not be saved to Risk_Score: {save_exc}")
                else:
                    st.info("This is a new-condition scenario only. It has not been attached to a batch or saved to the database.")
                with st.expander("View model input values"):
                    st.dataframe(input_df, use_container_width=True, hide_index=True)
            except Exception as exc:
                st.error(f"Prediction failed: {exc}")

    metrics_path = APP_DIR / "trained_model_metrics.json"
    if metrics_path.exists():
        try:
            import json
            with open(metrics_path, "r", encoding="utf-8") as file:
                metrics = json.load(file)
            st.markdown("### Evaluation on held-out synthetic test data")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Accuracy", f"{metrics['accuracy'] * 100:.1f}%")
            m2.metric("Precision", f"{metrics['precision'] * 100:.1f}%")
            m3.metric("Recall", f"{metrics['recall'] * 100:.1f}%")
            m4.metric("ROC-AUC", f"{metrics['roc_auc']:.3f}")
            st.caption(f"Dataset rows used: {metrics.get('rows_used', '—')}. Synthetic-data metrics do not establish real-world food-safety performance.")
            if "confusion_matrix" in metrics:
                st.write("Confusion matrix (rows = actual class 0/1; columns = predicted class 0/1)")
                st.dataframe(pd.DataFrame(metrics["confusion_matrix"], index=["Actual 0", "Actual 1"], columns=["Predicted 0", "Predicted 1"]), use_container_width=True)
        except Exception as exc:
            st.warning(f"Could not read trained_model_metrics.json: {exc}")

st.sidebar.divider()
st.sidebar.caption(f"Database: {DB_PATH.name}")
st.sidebar.caption("Demonstration build — verify records before real-world use.")
