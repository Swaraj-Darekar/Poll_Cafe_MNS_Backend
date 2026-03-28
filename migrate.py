import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

def migrate():
    print("Starting migration...")
    
    # We can't run raw SQL easily via the client without RPC, 
    # but we can try to check if columns exist by fetching 1 row
    try:
        # Check wallet_balance in settings
        res = supabase.table("settings").select("wallet_balance").limit(1).execute()
        print("wallet_balance already exists.")
    except Exception as e:
        print("wallet_balance likely missing. Please run the following SQL in Supabase Dashboard:")
        print("ALTER TABLE settings ADD COLUMN IF NOT EXISTS wallet_balance NUMERIC DEFAULT 0;")

    try:
        # Check wallet_transactions table
        res = supabase.table("wallet_transactions").select("id").limit(1).execute()
        print("wallet_transactions table already exists.")
    except Exception as e:
        print("wallet_transactions table likely missing. Please run the following SQL in Supabase Dashboard:")
        print("CREATE TABLE IF NOT EXISTS wallet_transactions (id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, type TEXT CHECK (type IN ('credit', 'debit')), amount NUMERIC NOT NULL, reason TEXT, created_at TIMESTAMPTZ DEFAULT NOW());")

if __name__ == "__main__":
    migrate()
