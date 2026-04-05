-- ==========================================
-- POOL CAFE MANAGEMENT SYSTEM: FINAL PROD SCHEMA
-- ==========================================

-- 1. Settings Table
CREATE TABLE IF NOT EXISTS settings (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    small_price_per_hour NUMERIC DEFAULT 100,
    big_price_per_hour NUMERIC DEFAULT 150,
    sd_price_per_hour NUMERIC DEFAULT 200,
    upi_id TEXT DEFAULT 'yourname@upi',
    merchant_name TEXT DEFAULT 'Pool Cafe',
    mcc TEXT DEFAULT '0000',
    wallet_balance NUMERIC DEFAULT 0,
    is_commission_enabled BOOLEAN DEFAULT TRUE,
    commission_per_booking NUMERIC DEFAULT 5.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed Initial settings (If not exists)
INSERT INTO settings (id, small_price_per_hour, big_price_per_hour, sd_price_per_hour, upi_id, wallet_balance)
VALUES (1, 100, 150, 200, 'yourname@upi', 20.0)
ON CONFLICT (id) DO NOTHING;

-- 2. Tables Table
CREATE TABLE IF NOT EXISTS tables (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    table_number INT UNIQUE NOT NULL,
    type TEXT CHECK (type IN ('small', 'big', 'sd')) NOT NULL,
    is_walkin_reserved BOOLEAN DEFAULT FALSE,
    status TEXT CHECK (status IN ('available', 'occupied')) DEFAULT 'available',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed Initial tables (If empty)
INSERT INTO tables (table_number, type, is_walkin_reserved) VALUES 
(1, 'small', FALSE),
(2, 'small', FALSE),
(3, 'small', FALSE),
(4, 'small', FALSE),
(5, 'sd', FALSE),
(6, 'big', FALSE),
(7, 'small', TRUE)
ON CONFLICT (table_number) DO NOTHING;

-- 3. Sessions Table
CREATE TABLE IF NOT EXISTS sessions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    table_id BIGINT REFERENCES tables(id),
    customer_name TEXT NOT NULL,
    customer_phone TEXT NOT NULL,
    start_time TIMESTAMPTZ DEFAULT NOW(),
    end_time TIMESTAMPTZ,
    total_minutes INT,
    total_amount NUMERIC DEFAULT 0,
    gross_amount NUMERIC DEFAULT 0,
    commission_amount NUMERIC DEFAULT 0,
    advance_amount NUMERIC DEFAULT 0,
    extra_amount NUMERIC DEFAULT 0,
    discount_amount NUMERIC DEFAULT 0,
    payment_status TEXT DEFAULT 'pending',
    payment_method TEXT DEFAULT 'online',
    booking_id BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Bookings Table
CREATE TABLE IF NOT EXISTS bookings (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    table_id BIGINT REFERENCES tables(id),
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    booking_time TIMESTAMPTZ NOT NULL,
    duration NUMERIC DEFAULT 1,
    advance_paid NUMERIC DEFAULT 100.0,
    payment_status TEXT DEFAULT 'paid',
    status TEXT DEFAULT 'pending_admin',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Menu Table
CREATE TABLE IF NOT EXISTS menu (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    price NUMERIC NOT NULL,
    category TEXT DEFAULT 'uncategorized',
    is_available BOOLEAN DEFAULT TRUE,
    image_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Expenses Table
CREATE TABLE IF NOT EXISTS expenses (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Wallet Transactions
CREATE TABLE IF NOT EXISTS wallet_transactions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    type TEXT CHECK (type IN ('credit', 'debit')) NOT NULL,
    amount NUMERIC NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. SuperAdmin Settlements
CREATE TABLE IF NOT EXISTS superadmin_settlements (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    month_name TEXT NOT NULL,
    year INT NOT NULL,
    total_bookings INT DEFAULT 0,
    total_earnings NUMERIC DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
