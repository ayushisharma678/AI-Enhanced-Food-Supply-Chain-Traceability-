-- 1. Insert Farmer (without registered_on column)
INSERT OR REPLACE INTO Farmer (farmer_id, name, contact_no, farm_location) 
VALUES (1, 'R. Selvam', '9876543210', 'Salem, Tamil Nadu');

-- 2. Insert Master Entities
INSERT OR REPLACE INTO Collection_Center (center_id, name, location) 
VALUES (1, 'Salem Agri Collection Point', 'Salem');

INSERT OR REPLACE INTO Processing_Plant (plant_id, name, location, license_no) 
VALUES (1, 'Apex Agro Processing', 'Coimbatore', 'LIC-TN-2026-88');

INSERT OR REPLACE INTO Warehouse (warehouse_id, name, location, capacity_kg) 
VALUES (1, 'Central Cold Storage Warehouse', 'Erode', 50000.00);

INSERT OR REPLACE INTO Transporter (transporter_id, name, vehicle_no, contact_no) 
VALUES (1, 'Express Agri Logistics', 'TN-37-AB-1234', '9123456789');

INSERT OR REPLACE INTO Retail_Store (store_id, name, location) 
VALUES (1, 'FreshMart Supermarket', 'Chennai');

-- 3. Insert Test Batch
INSERT OR REPLACE INTO Batch (batch_id, farmer_id, crop_type, harvest_date, quantity_kg, status) 
VALUES ('BATCH-2026-000123', 1, 'Tomato', '2026-08-20', 1000.00, 'Delivered');

-- 4. Insert Complete Supply Chain Lifecycle Records
INSERT OR REPLACE INTO Collection_Record (record_id, batch_id, center_id, received_date, grade) 
VALUES (1, 'BATCH-2026-000123', 1, '2026-08-21', 'Grade A');

INSERT OR REPLACE INTO Processing_Record (record_id, batch_id, plant_id, process_date, process_type, output_qty_kg) 
VALUES (1, 'BATCH-2026-000123', 1, '2026-08-22', 'Washing & Sorting', 950.00);

INSERT OR REPLACE INTO Storage_Record (storage_id, batch_id, warehouse_id, in_date, out_date, temperature_c, humidity_pct) 
VALUES (1, 'BATCH-2026-000123', 1, '2026-08-22', '2026-08-25', 4.50, 85.00);

INSERT OR REPLACE INTO Transport_Log (transport_id, batch_id, transporter_id, origin, destination, dispatch_time, arrival_time, transit_temp_c) 
VALUES (1, 'BATCH-2026-000123', 1, 'Erode', 'Chennai', '2026-08-25 04:00:00', '2026-08-25 09:30:00', 5.20);

INSERT OR REPLACE INTO Retail_Inventory (inventory_id, batch_id, store_id, received_date, quantity_kg, unit_price) 
VALUES (1, 'BATCH-2026-000123', 1, '2026-08-25', 950.00, 45.00);

-- 5. Insert AI Risk Score
INSERT OR REPLACE INTO Risk_Score (score_id, batch_id, model_version, predicted_risk, risk_level, scored_on, top_features) 
VALUES (1, 'BATCH-2026-000123', 'v1.0.0', 0.18, 'Low', '2026-08-25 10:00:00', 'Storage_Temp,Transit_Time');