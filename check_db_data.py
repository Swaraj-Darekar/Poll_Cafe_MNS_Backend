import asyncio
from database import get_db
from datetime import datetime, timezone, timedelta

async def check_data():
    db = get_db()
    try:
        # Check settlements
        settlements = db.table("settlements").select("id, created_at, month, total_revenue").order("created_at", desc=True).limit(5).execute()
        print("Latest 5 Settlements:")
        for s in settlements.data:
            print(f"ID: {s['id']}, Date: {s['created_at']}, Revenue: {s['total_revenue']}")
            
        # Check sessions (latest paid today)
        IST = timezone(timedelta(hours=5, minutes=30))
        now_utc = datetime.now(timezone.utc)
        # Business day start at 4:30 AM IST
        biz_today_start_ist = now_utc.astimezone(IST).replace(hour=4, minute=30, second=0, microsecond=0)
        today_start = biz_today_start_ist.astimezone(timezone.utc)
        
        print(f"\nBusiness Today Start (UTC): {today_start}")
        
        sessions = db.table("sessions")\
            .select("id, end_time, total_amount, payment_status")\
            .eq("payment_status", "paid")\
            .gte("end_time", today_start.isoformat())\
            .order("end_time", desc=True)\
            .limit(10)\
            .execute()
        
        print("\nLatest 10 Sessions (Paid Today):")
        for s in sessions.data:
            print(f"ID: {s['id']}, End Time: {s['end_time']}, Amount: {s['total_amount']}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_data())
