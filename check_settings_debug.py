import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import get_db

def check_settings():
    db = get_db()
    response = db.table("settings").select("*").order("updated_at", desc=True).limit(1).execute()
    if response.data:
        print("SETTINGS DATA:", response.data[0])
        print("is_commission_enabled:", response.data[0].get("is_commission_enabled"))
        print("commission_per_booking:", response.data[0].get("commission_per_booking"))
    else:
        print("NO SETTINGS FOUND")

if __name__ == "__main__":
    check_settings()
