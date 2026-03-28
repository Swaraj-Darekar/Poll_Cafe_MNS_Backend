import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

def migrate():
    print("Running migrations for Super Admin enhancements...")
    
    # 1. Add commission_per_booking to settings
    try:
        print("Please ensure you run this SQL in Supabase:")
        print("ALTER TABLE settings ADD COLUMN IF NOT EXISTS commission_per_booking NUMERIC DEFAULT 5;")
        print("ALTER TABLE settings ADD COLUMN IF NOT EXISTS last_superadmin_settlement_at TIMESTAMPTZ DEFAULT NOW();")
        print("""
        CREATE TABLE IF NOT EXISTS superadmin_settlements (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            month_name TEXT,
            year INT,
            total_bookings INT,
            total_earnings NUMERIC,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """)
    except Exception as e:
        print(f"Migration error: {e}")

if __name__ == "__main__":
    migrate()
