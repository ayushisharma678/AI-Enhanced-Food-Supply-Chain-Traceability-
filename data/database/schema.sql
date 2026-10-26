-- ============================================================
-- AI-Enhanced Food Supply Chain Traceability & Contamination
-- Risk Prediction -- SQLite Relational Schema (Review 2)
-- Database Systems Laboratory | Fall 2026-2027
-- ============================================================
-- This schema is written for the SQLite prototype used in Review 2.
-- PostgreSQL/Supabase migration is planned for Review 3.

PRAGMA foreign_keys = ON;


-- ============================================================
-- 1. CORE ACTOR / MASTER TABLES
-- ============================================================

CREATE TABLE Farmer (
    farmer_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    contact_no      TEXT,
    farm_location   TEXT,
    registered_on   TEXT DEFAULT CURRENT_DATE
);


CREATE TABLE Collection_Center (
    center_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    location        TEXT
);


CREATE TABLE Processing_Plant (
    plant_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    location        TEXT,
    license_no      TEXT
);


CREATE TABLE Warehouse (
    warehouse_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    location        TEXT,
    capacity_kg     REAL
);


CREATE TABLE Transporter (
    transporter_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    vehicle_no      TEXT,
    contact_no      TEXT
);


CREATE TABLE Retail_Store (
    store_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    location        TEXT
);


-- ============================================================
-- 2. BATCH TABLE
--    Central table for complete traceability
-- ============================================================

CREATE TABLE Batch (
    batch_id        TEXT PRIMARY KEY,
    farmer_id       INTEGER NOT NULL,
    crop_type       TEXT NOT NULL,
    harvest_date    TEXT NOT NULL,
    quantity_kg     REAL NOT NULL,
    status          TEXT NOT NULL DEFAULT 'Harvested'
                    CHECK (
                        status IN (
                            'Harvested',
                            'Processing',
                            'Stored',
                            'In_Transit',
                            'Delivered',
                            'Retail',
                            'Sold',
                            'Recalled'
                        )
                    ),

    FOREIGN KEY (farmer_id)
        REFERENCES Farmer(farmer_id)
);


-- ============================================================
-- 3. COLLECTION RECORD
-- ============================================================

CREATE TABLE Collection_Record (
    record_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id        TEXT NOT NULL,
    center_id       INTEGER NOT NULL,
    received_date   TEXT NOT NULL,
    grade           TEXT,

    FOREIGN KEY (batch_id)
        REFERENCES Batch(batch_id),

    FOREIGN KEY (center_id)
        REFERENCES Collection_Center(center_id)
);


-- ============================================================
-- 4. PROCESSING RECORD
-- ============================================================

CREATE TABLE Processing_Record (
    record_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id        TEXT NOT NULL,
    plant_id        INTEGER NOT NULL,
    process_date    TEXT NOT NULL,
    process_type    TEXT,
    output_qty_kg   REAL,

    FOREIGN KEY (batch_id)
        REFERENCES Batch(batch_id),

    FOREIGN KEY (plant_id)
        REFERENCES Processing_Plant(plant_id)
);


-- ============================================================
-- 5. STORAGE RECORD
-- ============================================================

CREATE TABLE Storage_Record (
    storage_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id        TEXT NOT NULL,
    warehouse_id    INTEGER NOT NULL,
    in_date         TEXT NOT NULL,
    out_date        TEXT,
    temperature_c   REAL,
    humidity_pct    REAL,

    FOREIGN KEY (batch_id)
        REFERENCES Batch(batch_id),

    FOREIGN KEY (warehouse_id)
        REFERENCES Warehouse(warehouse_id)
);


-- ============================================================
-- 6. TRANSPORT LOG
-- ============================================================

CREATE TABLE Transport_Log (
    transport_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id        TEXT NOT NULL,
    transporter_id  INTEGER NOT NULL,
    origin          TEXT,
    destination     TEXT,
    dispatch_time   TEXT,
    arrival_time    TEXT,
    transit_temp_c  REAL,

    FOREIGN KEY (batch_id)
        REFERENCES Batch(batch_id),

    FOREIGN KEY (transporter_id)
        REFERENCES Transporter(transporter_id)
);


-- ============================================================
-- 7. RETAIL INVENTORY
-- ============================================================

CREATE TABLE Retail_Inventory (
    inventory_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id        TEXT NOT NULL,
    store_id        INTEGER NOT NULL,
    received_date   TEXT NOT NULL,
    quantity_kg     REAL,
    unit_price      REAL,

    FOREIGN KEY (batch_id)
        REFERENCES Batch(batch_id),

    FOREIGN KEY (store_id)
        REFERENCES Retail_Store(store_id)
);


-- ============================================================
-- 8. INSPECTION / QUALITY RECORD
-- ============================================================

CREATE TABLE Inspection (
    inspection_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id            TEXT NOT NULL,
    stage               TEXT,
    inspector_name      TEXT,
    inspection_date     TEXT NOT NULL,
    result              TEXT DEFAULT 'Pass',
    contamination_type  TEXT,
    notes               TEXT,

    FOREIGN KEY (batch_id)
        REFERENCES Batch(batch_id)
);


-- ============================================================
-- 9. AI RISK SCORE
-- ============================================================

CREATE TABLE Risk_Score (
    score_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id        TEXT NOT NULL,
    model_version   TEXT,
    predicted_risk  REAL,
    risk_level      TEXT,
    scored_on       TEXT DEFAULT CURRENT_TIMESTAMP,
    top_features    TEXT,

    FOREIGN KEY (batch_id)
        REFERENCES Batch(batch_id)
);


-- ============================================================
-- INDEXES (speed up batch_id lookups used by traceability queries)
-- ============================================================

CREATE INDEX idx_batch_farmer      ON Batch(farmer_id);
CREATE INDEX idx_collection_batch  ON Collection_Record(batch_id);
CREATE INDEX idx_processing_batch  ON Processing_Record(batch_id);
CREATE INDEX idx_storage_batch     ON Storage_Record(batch_id);
CREATE INDEX idx_transport_batch   ON Transport_Log(batch_id);
CREATE INDEX idx_retail_batch      ON Retail_Inventory(batch_id);
CREATE INDEX idx_inspection_batch  ON Inspection(batch_id);
CREATE INDEX idx_risk_batch        ON Risk_Score(batch_id);


-- ============================================================
-- 10. TRACEABILITY QUERY
--     Retrieves complete farm-to-retail journey.
--     NOTE: if a batch has several storage/transport/risk rows, this single
--     join returns one row per combination. The dashboard (app.py) therefore
--     queries each stage separately and shows the latest risk score.
-- ============================================================

-- SELECT
--     b.batch_id,
--     f.name AS farmer,
--     cr.received_date AS collected_on,
--     pr.process_date,
--     sr.warehouse_id,
--     sr.in_date,
--     sr.out_date,
--     tl.dispatch_time,
--     tl.arrival_time,
--     ri.store_id,
--     ri.received_date AS retail_date,
--     rs.predicted_risk,
--     rs.risk_level
--
-- FROM Batch b
--
-- JOIN Farmer f
--     ON b.farmer_id = f.farmer_id
--
-- LEFT JOIN Collection_Record cr
--     ON b.batch_id = cr.batch_id
--
-- LEFT JOIN Processing_Record pr
--     ON b.batch_id = pr.batch_id
--
-- LEFT JOIN Storage_Record sr
--     ON b.batch_id = sr.batch_id
--
-- LEFT JOIN Transport_Log tl
--     ON b.batch_id = tl.batch_id
--
-- LEFT JOIN Retail_Inventory ri
--     ON b.batch_id = ri.batch_id
--
-- LEFT JOIN Risk_Score rs
--     ON b.batch_id = rs.batch_id
--
-- WHERE b.batch_id = 'BATCH-2026-000123';