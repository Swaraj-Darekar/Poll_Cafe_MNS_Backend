-- Menu Table Schema
CREATE TABLE IF NOT EXISTS menu (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    price NUMERIC NOT NULL,
    category TEXT DEFAULT 'Others',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Initial Menu Data
INSERT INTO menu (name, price, category) VALUES 
('Cold Drink (250ml)', 25, 'Drinks'),
('Water Bottle (1L)', 20, 'Drinks'),
('Soda (600ml)', 40, 'Drinks'),
('Snacks (Large)', 50, 'Snacks'),
('Tea / Coffee', 15, 'Drinks');
