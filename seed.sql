-- ============================================================
-- AI-Enhanced Food Supply Chain Traceability
-- Seed Data - SQLite Prototype
-- Database Systems Laboratory | Fall 2026-2027
-- ============================================================


-- ============================================================
-- 1. Insert Farmer
-- ============================================================

INSERT OR REPLACE INTO Farmer
    (farmer_id, name, contact_no, farm_location)
VALUES
    (1,
     'R. Selvam',
     '9876543210',
     'Salem, Tamil Nadu');


-- ============================================================
-- 2. Insert Master Entities
-- ============================================================

INSERT OR REPLACE INTO Collection_Center
    (center_id, name, location)
VALUES
    (1,
     'Salem Agri Collection Point',
     'Salem');


INSERT OR REPLACE INTO Processing_Plant
    (plant_id, name, location, license_no)
VALUES
    (1,
     'Apex Agro Processing',
     'Coimbatore',
     'LIC-TN-2026-88');


INSERT OR REPLACE INTO Warehouse
    (warehouse_id, name, location, capacity_kg)
VALUES
    (1,
     'Central Cold Storage Warehouse',
     'Erode',
     50000.00);


INSERT OR REPLACE INTO Transporter
    (transporter_id, name, vehicle_no, contact_no)
VALUES
    (1,
     'Express Agri Logistics',
     'TN-37-AB-1234',
     '9123456789');


INSERT OR REPLACE INTO Retail_Store
    (store_id, name, location)
VALUES
    (1,
     'FreshMart Supermarket',
     'Chennai');


-- ============================================================
-- 3. Insert Test Batch
-- ============================================================
-- The batch has completed transportation and has reached the
-- retail store, so its lifecycle status is set to 'Retail' --
-- matching the Batch.status values allowed by the schema
-- (Harvested, Processing, Stored, In_Transit, Delivered, Retail, Sold, Recalled).

INSERT OR REPLACE INTO Batch
    (batch_id, farmer_id, crop_type, harvest_date, quantity_kg, status)
VALUES
    ('BATCH-2026-000123',
     1,
     'Tomato',
     '2026-08-20',
     1000.00,
     'Retail');


-- ============================================================
-- 4. Insert Complete Supply Chain Lifecycle Records
-- ============================================================

-- ------------------------------------------------------------
-- 4.1 Collection
-- ------------------------------------------------------------

INSERT OR REPLACE INTO Collection_Record
    (record_id, batch_id, center_id, received_date, grade)
VALUES
    (1,
     'BATCH-2026-000123',
     1,
     '2026-08-21',
     'Grade A');


-- ------------------------------------------------------------
-- 4.2 Processing
-- ------------------------------------------------------------

INSERT OR REPLACE INTO Processing_Record
    (record_id, batch_id, plant_id, process_date, process_type, output_qty_kg)
VALUES
    (1,
     'BATCH-2026-000123',
     1,
     '2026-08-22',
     'Washing & Sorting',
     950.00);


-- ------------------------------------------------------------
-- 4.3 Storage
-- ------------------------------------------------------------

INSERT OR REPLACE INTO Storage_Record
    (storage_id, batch_id, warehouse_id, in_date, out_date,
     temperature_c, humidity_pct)
VALUES
    (1,
     'BATCH-2026-000123',
     1,
     '2026-08-22',
     '2026-08-25',
     4.50,
     85.00);


-- ------------------------------------------------------------
-- 4.4 Transportation
-- ------------------------------------------------------------

INSERT OR REPLACE INTO Transport_Log
    (transport_id, batch_id, transporter_id, origin, destination,
     dispatch_time, arrival_time, transit_temp_c)
VALUES
    (1,
     'BATCH-2026-000123',
     1,
     'Erode',
     'Chennai',
     '2026-08-25 04:00:00',
     '2026-08-25 09:30:00',
     5.20);


-- ------------------------------------------------------------
-- 4.5 Retail Inventory
-- ------------------------------------------------------------

INSERT OR REPLACE INTO Retail_Inventory
    (inventory_id, batch_id, store_id, received_date,
     quantity_kg, unit_price)
VALUES
    (1,
     'BATCH-2026-000123',
     1,
     '2026-08-25',
     950.00,
     45.00);


-- ============================================================
-- 5. Insert Quality Inspection Record
-- ============================================================
-- Inspection is linked to the batch through batch_id.
-- This record represents the quality inspection performed
-- during the processing stage.

INSERT OR REPLACE INTO Inspection
    (inspection_id, batch_id, stage, inspector_name,
     inspection_date, result, contamination_type, notes)
VALUES
    (1,
     'BATCH-2026-000123',
     'Processing',
     'K. Meena',
     '2026-08-22',
     'Pass',
     NULL,
     'No visible defects');


-- ============================================================
-- 6. Insert AI Risk Score
-- ============================================================
-- Risk score generated by the prototype AI risk engine.
-- predicted_risk is represented as a value between 0 and 1.

INSERT OR REPLACE INTO Risk_Score
    (score_id, batch_id, model_version, predicted_risk,
     risk_level, scored_on, top_features)
VALUES
    (1,
     'BATCH-2026-000123',
     'v1.0.0',
     0.18,
     'Low',
     '2026-08-25 10:00:00',
     'Storage_Temp,Transit_Time');