import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

def migrate_upi():
    print("--- Business UPI Migration Check ---")
    
    # 1. Check merchant_name and mcc in settings table
    try:
        # Check merchant_name
        supabase.table("settings").select("merchant_name").limit(1).execute()
        print("[✓] merchant_name already exists.")
    except Exception:
        print("[!] merchant_name missing. SQL to run:")
        print("ALTER TABLE settings ADD COLUMN IF NOT EXISTS merchant_name TEXT DEFAULT 'Pool Cafe';")

    try:
        # Check mcc
        supabase.table("settings").select("mcc").limit(1).execute()
        print("[✓] mcc already exists.")
    except Exception:
        print("[!] mcc missing. SQL to run:")
        print("ALTER TABLE settings ADD COLUMN IF NOT EXISTS mcc TEXT DEFAULT '0000';")

    print("\n--- Summary ---")
    print("If you see [!] above, please copy and paste the SQL commands into your Supabase SQL Editor.")

if __name__ == "__main__":
    migrate_upi()
