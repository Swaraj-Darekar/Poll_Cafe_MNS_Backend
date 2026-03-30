import asyncio
from database import get_db
import datetime

async def test():
    try:
        db = get_db()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        session_data = {
            "table_id": None,
            "customer_name": "Take Away",
            "customer_phone": "0000000000",
            "start_time": now,
            "end_time": now,
            "total_minutes": 0,
            "total_amount": 50.0,
            "gross_amount": 50.0,
            "commission_amount": 0,
            "payment_status": "paid",
            "payment_method": 'online',
        }
        res = db.table("sessions").insert(session_data).execute()
        print("Insert Success:", res.data)
    except Exception as e:
        print("Insert Failed:", e)

asyncio.run(test())
