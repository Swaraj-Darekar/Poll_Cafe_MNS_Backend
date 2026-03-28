-- SQL Schema for Pool Cafe Management System

-- 1. Settings Table
CREATE TABLE IF NOT EXISTS settings (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    small_price_per_hour INT DEFAULT 100,
    big_price_per_hour INT DEFAULT 150,
    upi_id TEXT DEFAULT 'example@upi',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Initial Settings
INSERT INTO settings (small_price_per_hour, big_price_per_hour, upi_id) VALUES (100, 150, 'yourname@upi');

-- 2. Tables Table
CREATE TABLE IF NOT EXISTS tables (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    table_number INT UNIQUE NOT NULL,
    type TEXT CHECK (type IN ('small', 'big')) NOT NULL,
    is_walkin_reserved BOOLEAN DEFAULT FALSE,
    status TEXT CHECK (status IN ('available', 'occupied')) DEFAULT 'available',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Initial Tables Data
INSERT INTO tables (table_number, type, is_walkin_reserved, status) VALUES 
(1, 'small', FALSE, 'available'),
(2, 'small', FALSE, 'available'),
(3, 'small', FALSE, 'available'),
(4, 'small', FALSE, 'available'),
(5, 'small', FALSE, 'available'),
(6, 'big', FALSE, 'available'),
(7, 'small', TRUE, 'available');

-- 3. Sessions Table (Core Logic)
CREATE TABLE IF NOT EXISTS sessions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    table_id BIGINT REFERENCES tables(id),
    customer_name TEXT NOT NULL,
    customer_phone TEXT NOT NULL,
    start_time TIMESTAMPTZ DEFAULT NOW(),
    end_time TIMESTAMPTZ,
    total_minutes INT,
    total_amount NUMERIC,
    payment_status TEXT CHECK (payment_status IN ('pending', 'paid')) DEFAULT 'pending',
    payment_method TEXT CHECK (payment_method IN ('cash', 'online')) DEFAULT 'online'
);
