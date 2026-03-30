import os
from supabase import create_client
from dotenv import load_dotenv

# Load from backend dir
load_dotenv('backend/.env')

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

print("--- TABLES ---")
res = supabase.table("tables").select("*").eq("table_number", 5).execute()
print(res.data)

print("\n--- SETTINGS ---")
res = supabase.table("settings").select("*").eq("id", 1).execute()
print(res.data)
