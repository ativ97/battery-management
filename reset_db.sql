-- WARNING: This script will DELETE ALL DATA in your database.
-- Run this in the Neon Console SQL Editor to reset your database schema.

-- 1. Drop existing tables (Order matters due to potential foreign keys, though none are explicitly enforced here)
DROP TABLE IF EXISTS audit_scrap_batteries;
DROP TABLE IF EXISTS challan_batteries;
DROP TABLE IF EXISTS scrap_batteries;
DROP TABLE IF EXISTS exchanges;
DROP TABLE IF EXISTS batteries;
DROP TABLE IF EXISTS customers;

-- 2. Create Customers Table
CREATE TABLE customers (
    phone TEXT PRIMARY KEY,
    name TEXT,
    created_at TEXT
);

-- 3. Create Batteries Table
CREATE TABLE batteries (
    serial_no TEXT PRIMARY KEY,
    model_type TEXT,
    status TEXT,
    sold_date TEXT,
    date_of_purchase TEXT,
    warranty_expiry TEXT,
    current_owner_phone TEXT,
    ticket_id TEXT,
    vehicle_no TEXT,
    has_loaner BOOLEAN DEFAULT FALSE
);

-- 4. Create Exchanges Table
CREATE TABLE exchanges (
    id SERIAL PRIMARY KEY,
    date TEXT,
    old_battery_serial TEXT,
    new_battery_serial TEXT,
    customer_phone TEXT,
    action_taken TEXT,
    notes TEXT
);

-- 5. Create Scrap Batteries Table
CREATE TABLE scrap_batteries (
    serial_no TEXT PRIMARY KEY,
    model_type TEXT,
    received_date TEXT,
    customer_phone TEXT,
    ticket_id TEXT,
    notes TEXT
);

-- 6. Create Challan Batteries Table
CREATE TABLE challan_batteries (
    serial_no TEXT PRIMARY KEY,
    model_type TEXT,
    received_date TEXT,
    customer_phone TEXT,
    ticket_id TEXT,
    notes TEXT,
    challan_date TEXT
);

-- 7. Create Archived Scrap Batteries Table (Audit)
CREATE TABLE audit_scrap_batteries (
    serial_no TEXT PRIMARY KEY,
    model_type TEXT,
    received_date TEXT,
    customer_phone TEXT,
    ticket_id TEXT,
    notes TEXT,
    challan_date TEXT,
    final_archived_date TEXT
);

-- Verification
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
