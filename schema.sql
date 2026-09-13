-- ============================================================
-- AI-Enhanced Food Supply Chain Traceability & Contamination
-- Risk Prediction -- Relational Schema (Review 2)
-- Database Systems Laboratory | Fall 2026-2027
-- ============================================================

CREATE DATABASE IF NOT EXISTS food_traceability;
USE food_traceability;

-- ---------- Core actor tables ----------

CREATE TABLE Farmer (
    farmer_id       INT PRIMARY KEY AUTO_INCREMENT,
    name            VARCHAR(100) NOT NULL,
    contact_no      VARCHAR(15),
    farm_location   VARCHAR(150),
    registered_on   DATE DEFAULT (CURRENT_DATE)
);

CREATE TABLE Collection_Center (
    center_id       INT PRIMARY KEY AUTO_INCREMENT,
    name            VARCHAR(100) NOT NULL,
    location        VARCHAR(150)
);

CREATE TABLE Processing_Plant (
    plant_id        INT PRIMARY KEY AUTO_INCREMENT,
    name            VARCHAR(100) NOT NULL,
    location        VARCHAR(150),
    license_no      VARCHAR(50)
);

CREATE TABLE Warehouse (
    warehouse_id    INT PRIMARY KEY AUTO_INCREMENT,
    name            VARCHAR(100) NOT NULL,
    location        VARCHAR(150),
    capacity_kg     DECIMAL(10,2)
);

CREATE TABLE Transporter (
    transporter_id  INT PRIMARY KEY AUTO_INCREMENT,
    name            VARCHAR(100) NOT NULL,
    vehicle_no      VARCHAR(20),
    contact_no      VARCHAR(15)
);

CREATE TABLE Retail_Store (
    store_id        INT PRIMARY KEY AUTO_INCREMENT,
    name            VARCHAR(100) NOT NULL,
    location        VARCHAR(150)
);

-- ---------- Batch: the traceability backbone ----------

CREATE TABLE Batch (
    batch_id        VARCHAR(20) PRIMARY KEY,       -- e.g. BATCH-2026-000123
    farmer_id       INT NOT NULL,
    crop_type       VARCHAR(50) NOT NULL,
    harvest_date    DATE NOT NULL,
    quantity_kg     DECIMAL(10,2) NOT NULL,
    status          ENUM('Harvested','Processing','Stored','In_Transit',
                          'Retail','Recalled','Sold') DEFAULT 'Harvested',
    FOREIGN KEY (farmer_id) REFERENCES Farmer(farmer_id)
);

-- ---------- Stage-linked records (each keys off batch_id) ----------

CREATE TABLE Collection_Record (
    record_id       INT PRIMARY KEY AUTO_INCREMENT,
    batch_id        VARCHAR(20) NOT NULL,
    center_id       INT NOT NULL,
    received_date   DATE NOT NULL,
    grade           VARCHAR(20),
    FOREIGN KEY (batch_id) REFERENCES Batch(batch_id),
    FOREIGN KEY (center_id) REFERENCES Collection_Center(center_id)
);

CREATE TABLE Processing_Record (
    record_id       INT PRIMARY KEY AUTO_INCREMENT,
    batch_id        VARCHAR(20) NOT NULL,
    plant_id        INT NOT NULL,
    process_date    DATE NOT NULL,
    process_type    VARCHAR(50),               -- washing, sorting, packing...
    output_qty_kg   DECIMAL(10,2),
    FOREIGN KEY (batch_id) REFERENCES Batch(batch_id),
    FOREIGN KEY (plant_id) REFERENCES Processing_Plant(plant_id)
);

CREATE TABLE Storage_Record (
    storage_id      INT PRIMARY KEY AUTO_INCREMENT,
    batch_id        VARCHAR(20) NOT NULL,
    warehouse_id    INT NOT NULL,
    in_date         DATE NOT NULL,
    out_date        DATE,
    temperature_c   DECIMAL(4,1),
    humidity_pct    DECIMAL(4,1),
    FOREIGN KEY (batch_id) REFERENCES Batch(batch_id),
    FOREIGN KEY (warehouse_id) REFERENCES Warehouse(warehouse_id)
);

CREATE TABLE Transport_Log (
    transport_id    INT PRIMARY KEY AUTO_INCREMENT,
    batch_id        VARCHAR(20) NOT NULL,
    transporter_id  INT NOT NULL,
    origin          VARCHAR(150),
    destination     VARCHAR(150),
    dispatch_time   DATETIME,
    arrival_time    DATETIME,
    transit_temp_c  DECIMAL(4,1),
    FOREIGN KEY (batch_id) REFERENCES Batch(batch_id),
    FOREIGN KEY (transporter_id) REFERENCES Transporter(transporter_id)
);

CREATE TABLE Retail_Inventory (
    inventory_id    INT PRIMARY KEY AUTO_INCREMENT,
    batch_id        VARCHAR(20) NOT NULL,
    store_id        INT NOT NULL,
    received_date   DATE NOT NULL,
    quantity_kg     DECIMAL(10,2),
    unit_price      DECIMAL(8,2),
    FOREIGN KEY (batch_id) REFERENCES Batch(batch_id),
    FOREIGN KEY (store_id) REFERENCES Retail_Store(store_id)
);

-- ---------- Quality & AI tables ----------

CREATE TABLE Inspection (
    inspection_id   INT PRIMARY KEY AUTO_INCREMENT,
    batch_id        VARCHAR(20) NOT NULL,
    stage           ENUM('Collection','Processing','Storage','Transport','Retail'),
    inspector_name  VARCHAR(100),
    inspection_date DATE NOT NULL,
    result          ENUM('Pass','Fail','Flagged') DEFAULT 'Pass',
    contamination_type VARCHAR(50),            -- NULL if Pass
    notes           VARCHAR(255),
    FOREIGN KEY (batch_id) REFERENCES Batch(batch_id)
);

CREATE TABLE Risk_Score (
    score_id        INT PRIMARY KEY AUTO_INCREMENT,
    batch_id        VARCHAR(20) NOT NULL,
    model_version   VARCHAR(20),
    predicted_risk  DECIMAL(5,4),              -- 0.0000 - 1.0000
    risk_level      ENUM('Low','Medium','High') ,
    scored_on       DATETIME DEFAULT CURRENT_TIMESTAMP,
    top_features    VARCHAR(255),              -- e.g. "storage_temp, transit_time"
    FOREIGN KEY (batch_id) REFERENCES Batch(batch_id)
);

-- ---------- Example traceability query ----------
-- Full farm-to-retail journey for one batch:
--
-- SELECT b.batch_id, f.name AS farmer, cr.received_date AS collected_on,
--        pr.process_date, sr.warehouse_id, sr.in_date, sr.out_date,
--        tl.dispatch_time, tl.arrival_time, ri.store_id, ri.received_date AS retail_date,
--        rs.predicted_risk, rs.risk_level
-- FROM Batch b
-- JOIN Farmer f            ON b.farmer_id = f.farmer_id
-- LEFT JOIN Collection_Record cr ON b.batch_id = cr.batch_id
-- LEFT JOIN Processing_Record pr ON b.batch_id = pr.batch_id
-- LEFT JOIN Storage_Record sr    ON b.batch_id = sr.batch_id
-- LEFT JOIN Transport_Log tl     ON b.batch_id = tl.batch_id
-- LEFT JOIN Retail_Inventory ri  ON b.batch_id = ri.batch_id
-- LEFT JOIN Risk_Score rs        ON b.batch_id = rs.batch_id
-- WHERE b.batch_id = 'BATCH-2026-000123';
