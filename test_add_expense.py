import asyncio
from database import get_db
from datetime import datetime, timezone

async def test_add():
    try:
        db = get_db()
        new_expense = {
            "name": "Test Expense",
            "amount": 50.0,
            "date": "2026-03-29",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        res = db.table("expenses").insert(new_expense).execute()
        print("Success:", res.data)
    except Exception as e:
        print("Error:", str(e))

asyncio.run(test_add())
