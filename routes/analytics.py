from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from database import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])

class SettleRequest(BaseModel):
    month: str
    year: int
    total_expense: float

@router.get("/")
async def get_analytics(db=Depends(get_db)):
    try:
        now = datetime.now(timezone.utc)
        
        # 0. Find latest settlement date to determine "Cycle Start"
        latest_settlement = db.table("settlements")\
            .select("created_at")\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        if latest_settlement.data:
            # Use the exact timestamp of the last settlement
            cycle_start = datetime.fromisoformat(latest_settlement.data[0]["created_at"].replace('Z', '+00:00'))
        else:
            # Default to start of current month if no settlements exist
            cycle_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Today's start (00:00:00 UTC)
        today_start_calendar = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # EFFECTIVE Today Start: If settled today, today's "new" sales start from settlement time.
        # Otherwise, they start from midnight.
        today_start = max(today_start_calendar, cycle_start)
        
        # 1. Fetch Effective Today's Paid Sessions (Session Balances)
        # Select * to gracefully handle payment_method if it exists
        today_sessions = db.table("sessions")\
            .select("*")\
            .eq("payment_status", "paid")\
            .gte("end_time", today_start.isoformat())\
            .execute()
        
        # 1.1 Fetch Today's Paid Bookings (Advances)
        # Assuming bookings advance_paid is usually online, but we can default it to online.
        today_bookings = db.table("bookings")\
            .select("*")\
            .eq("payment_status", "paid")\
            .gte("created_at", today_start.isoformat())\
            .execute()
        
        # 2. Fetch "Current Cycle" Paid Sessions (Since last settlement)
        cycle_sessions = db.table("sessions")\
            .select("*")\
            .eq("payment_status", "paid")\
            .gte("end_time", cycle_start.isoformat())\
            .execute()
            
        # 2.1 Fetch "Current Cycle" Paid Bookings
        cycle_bookings = db.table("bookings")\
            .select("*")\
            .eq("payment_status", "paid")\
            .gte("created_at", cycle_start.isoformat())\
            .execute()

        # Calculation helper
        def aggregate(sessions, bookings):
            revenue = sum(item.get("total_amount", 0) or 0 for item in sessions) + \
                      sum(item.get("advance_paid", 0) or 0 for item in bookings)
            count = len(sessions) + len(bookings)
            
            # Calculate payment method breakdown
            cash_total = sum(item.get("total_amount", 0) or 0 for item in sessions if item.get("payment_method") == "cash")
            online_total = sum(item.get("total_amount", 0) or 0 for item in sessions if item.get("payment_method", "online") != "cash") + \
                           sum(item.get("advance_paid", 0) or 0 for item in bookings) # Assuming bookings are online
            
            return {
                "revenue": round(revenue, 2), 
                "bookings": count,
                "cash_total": round(cash_total, 2),
                "online_total": round(online_total, 2)
            }

        return {
            "today": aggregate(today_sessions.data or [], today_bookings.data or []),
            "cycle": aggregate(cycle_sessions.data or [], cycle_bookings.data or []),
            "cycle_start": cycle_start.isoformat()
        }
    except Exception as e:
        print(f"ERROR: Analytics fetch failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analytics failed: {str(e)}")

@router.get("/settlements")
async def get_settlement_history(db=Depends(get_db)):
    try:
        response = db.table("settlements")\
            .select("*")\
            .order("created_at", desc=True)\
            .execute()
        return response.data or []
    except Exception as e:
        print(f"ERROR: Settlements fetch failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch settlements: {str(e)}")

@router.post("/settle-month")
async def settle_month(data: SettleRequest, db=Depends(get_db)):
    try:
        # 1. Get current cycle data
        analytics = await get_analytics(db)
        revenue = analytics["cycle"]["revenue"]
        expense = data.total_expense
        profit = revenue - expense
        
        # 2. Save to settlements table
        settlement_data = {
            "month": data.month,
            "year": data.year,
            "total_revenue": revenue,
            "total_expense": expense,
            "profit_loss": profit,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        response = db.table("settlements").insert(settlement_data).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to save settlement")
            
        return {"message": "Month settled successfully", "settlement": response.data[0]}
    except Exception as e:
        print(f"ERROR: Settlement failed: {str(e)}")
        # Check if table exists, if not, it will fail.
        # This is expected until the table is created.
        raise HTTPException(status_code=500, detail=f"Settlement failed: {str(e)}")
