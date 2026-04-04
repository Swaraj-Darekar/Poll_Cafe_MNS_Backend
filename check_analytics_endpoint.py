import asyncio
from database import get_db
from routes.analytics import get_session_history
import json

async def test_history():
    db = get_db()
    try:
        print("Testing /analytics/history endpoint logic...")
        result = await get_session_history(db)
        print(f"Success! Found {len(result)} days of history.")
        if len(result) > 0:
            print(f"Latest day: {result[0]['label']} with {len(result[0]['sessions'])} sessions.")
            # Print first session of latest day to verify fields
            if len(result[0]['sessions']) > 0:
                s = result[0]['sessions'][0]
                print(f"Sample Session ID: {s['id']}, Table: {s['table_name']}, Amount: {s['total_amount']}")
                print(f"Fields check: commission_amount={s.get('commission_amount')}, discount={s.get('discount')}")
        else:
            print("No history found in the last 30 days.")
    except Exception as e:
        print(f"ERROR: Endpoint logic failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_history())
