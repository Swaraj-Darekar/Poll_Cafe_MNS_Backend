import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

def check_db():
    print("Checking database settings...")
    try:
        res = supabase.table("settings").select("*").execute()
        print(f"Found {len(res.data)} settings rows.")
        for row in res.data:
            print(f"ID: {row['id']}, Wallet: {row.get('wallet_balance')}, Updated: {row.get('updated_at')}")
    except Exception as e:
        print(f"Error checking settings: {e}")

if __name__ == "__main__":
    check_db()
