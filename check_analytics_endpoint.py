import asyncio
from database import get_db
from routes.analytics import get_analytics

async def check_analytics():
    db = get_db()
    res = await get_analytics(db)
    print("Today:", res["today"])
    print("Cycle:", res["cycle"])
    print("Cycle Start:", res["cycle_start"])
    print("Business Today Start:", res["business_today_start"])

if __name__ == "__main__":
    asyncio.run(check_analytics())
