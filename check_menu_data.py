import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv('backend/.env')

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

print("--- MENU TABLE CONTENT ---")
try:
    res = supabase.table("menu").select("*").execute()
    print(res.data)
except Exception as e:
    print(f"Error: {e}")
