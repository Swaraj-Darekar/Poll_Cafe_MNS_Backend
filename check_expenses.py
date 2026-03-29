from database import get_db

db = get_db()
try:
    res = db.table("expenses").select("*").limit(1).execute()
    print("Expenses table EXISTS.")
except Exception as e:
    print("Expenses table ERROR:", str(e))
