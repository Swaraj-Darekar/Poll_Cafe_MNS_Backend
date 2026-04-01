import asyncio
from database import get_db
from routes.analytics import get_analytics
from datetime import datetime, timezone

async def test():
    db = next(get_db())
    try:
        res = await get_analytics(db)
        print("Analytics Result:")
        print(f"Today: {res['today']}")
        print(f"Cycle: {res['cycle']}")
        print(f"Cycle Start: {res['cycle_start']}")
        print(f"Business Today Start: {res['business_today_start']}")
        
        # Check latest settlement
        latest = db.table("settlements").select("created_at").order("created_at", desc=True).limit(1).execute()
        if latest.data:
            print(f"Latest Settlement in DB: {latest.data[0]['created_at']}")
        else:
            print("No settlements found")
            
        # Check one session to see its end_time
        sessions = db.table("sessions").select("end_time, total_amount").eq("payment_status", "paid").order("end_time", desc=True).limit(5).execute()
        print("\nLatest 5 Paid Sessions:")
        for s in sessions.data:
            print(f"End Time: {s['end_time']}, Amount: {s['total_amount']}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
