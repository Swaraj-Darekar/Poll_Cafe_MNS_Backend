import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

def migrate_extra_money():
    print("--- Extra Money & Discount Migration Check ---")
    
    # 1. Check extra_amount and discount_amount in sessions table
    try:
        # Check extra_amount
        supabase.table("sessions").select("extra_amount").limit(1).execute()
        print("[✓] extra_amount already exists.")
    except Exception:
        print("[!] extra_amount missing. SQL to run:")
        print("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS extra_amount NUMERIC DEFAULT 0;")

    try:
        # Check discount_amount
        supabase.table("sessions").select("discount_amount").limit(1).execute()
        print("[✓] discount_amount already exists.")
    except Exception:
        print("[!] discount_amount missing. SQL to run:")
        print("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS discount_amount NUMERIC DEFAULT 0;")

    print("\n--- Summary ---")
    print("If you see [!] above, please copy and paste the SQL command(s) into your Supabase SQL Editor.")

if __name__ == "__main__":
    migrate_extra_money()
