from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from database import get_db

router = APIRouter(prefix="/superadmin", tags=["superadmin"])

class WalletRequest(BaseModel):
    amount: float

class SuperAdminSettingsRequest(BaseModel):
    commission: float

class SettleRequest(BaseModel):
    month_name: str
    year: int
    total_bookings: int
    total_earnings: float

@router.get("/stats")
async def get_superadmin_stats(db=Depends(get_db)):
    try:
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # 0. Fetch Wallet Balance & Commission (Strictly Row ID: 1)
        # We fetch ID 1 to maintain consistency between environments.
        settings_res = db.table("settings").select("*").eq("id", 1).execute()
        
        wallet_balance = 0.0
        commission = 5.0
        
        if settings_res.data:
            s_data = settings_res.data[0]
            wallet_balance = float(s_data.get("wallet_balance") or 0.0)
            commission = float(s_data.get("commission_per_booking") or 5.0)
        else:
            # If ID 1 is missing, check if ANY settings exist as a fallback for old DBs
            fallback = db.table("settings").select("*").limit(1).execute()
            if fallback.data:
                s_data = fallback.data[0]
                wallet_balance = float(s_data.get("wallet_balance") or 0.0)
                commission = float(s_data.get("commission_per_booking") or 5.0)
        
        # 1. Today's Bookings (Paid sessions)
        # MUST use end_time to match analytics logic (when the sale was finalized)
        today_sessions = db.table("sessions")\
            .select("id")\
            .eq("payment_status", "paid")\
            .gte("end_time", start_of_day.isoformat())\
            .execute()
        today_count = len(today_sessions.data)
        
        # 2. Monthly Bookings (Calendar Month)
        month_sessions = db.table("sessions")\
            .select("id")\
            .eq("payment_status", "paid")\
            .gte("end_time", start_of_month.isoformat())\
            .execute()
        month_count = len(month_sessions.data)
        
        today_earnings = today_count * commission
        month_earnings = month_count * commission
        
        return {
            "today_bookings": today_count,
            "month_bookings": month_count,
            "today_earnings": today_earnings,
            "month_earnings": month_earnings,
            "wallet_balance": wallet_balance,
            "commission": commission
        }
    except Exception as e:
        print(f"ERROR in get_superadmin_stats: {e}")
        # Return partial data if possible instead of 500
        return {
            "today_bookings": 0,
            "month_bookings": 0,
            "today_earnings": 0,
            "month_earnings": 0,
            "wallet_balance": 0.0,
            "commission": 5.0,
            "error": str(e)
        }

@router.post("/wallet/add")
async def add_wallet_money(data: WalletRequest, db=Depends(get_db)):
    try:
        # Fetch current settings (Strictly ID: 1)
        settings = db.table("settings").select("*").eq("id", 1).execute()
        if not settings.data:
            # Fallback to any row if ID 1 isn't initialized yet
            settings = db.table("settings").select("*").limit(1).execute()
            if not settings.data:
                raise HTTPException(status_code=404, detail="Settings not found")
            
        sid = settings.data[0]["id"]
        current_balance = float(settings.data[0].get("wallet_balance", 0))
        new_balance = current_balance + data.amount
        
        # Update balance
        db.table("settings").update({"wallet_balance": new_balance}).eq("id", sid).execute()
        
        # Log transaction
        db.table("wallet_transactions").insert({
            "type": "credit",
            "amount": data.amount,
            "reason": "Add Money (Custom Amount)"
        }).execute()
        
        return {"new_balance": new_balance}
    except Exception as e:
        print(f"ERROR in add_wallet_money: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/settings")
async def update_superadmin_settings(data: SuperAdminSettingsRequest, db=Depends(get_db)):
    try:
        settings = db.table("settings").select("id").order("updated_at", desc=True).limit(1).execute()
        if not settings.data:
            raise HTTPException(status_code=404, detail="Settings not found")
        
        sid = settings.data[0]["id"]
        db.table("settings").update({"commission_per_booking": data.commission}).eq("id", sid).execute()
        return {"success": True, "new_commission": data.commission}
    except Exception as e:
        print(f"ERROR in update_superadmin_settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/settle")
async def superadmin_settle(data: SettleRequest, db=Depends(get_db)):
    try:
        # 1. Save settlement record
        db.table("superadmin_settlements").insert({
            "month_name": data.month_name,
            "year": data.year,
            "total_bookings": data.total_bookings,
            "total_earnings": data.total_earnings
        }).execute()
        
        return {"success": True}
    except Exception as e:
        print(f"ERROR in superadmin_settle: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset-system")
async def reset_system(db=Depends(get_db)):
    try:
        # Destructive Action: Delete all historical data
        
        # 1. Sessions & Bookings
        db.table("sessions").delete().neq("id", 0).execute()
        db.table("bookings").delete().neq("id", 0).execute()
        
        # 2. Financial History
        db.table("wallet_transactions").delete().neq("id", 0).execute()
        db.table("superadmin_settlements").delete().neq("id", 0).execute()
        db.table("expenses").delete().neq("id", 0).execute()
        try:
            db.table("monthly_settlements").delete().neq("id", 0).execute()
        except: pass
        
        # 3. Reset Wallet
        settings = db.table("settings").select("id").order("updated_at", desc=True).limit(1).execute()
        if settings.data:
            sid = settings.data[0]["id"]
            db.table("settings").update({
                "wallet_balance": 0.0
            }).eq("id", sid).execute()
            
        # 4. Reset Table status
        db.table("tables").update({"status": "available"}).neq("id", 0).execute()
        
        return {"success": True, "message": "System reset completed."}
    except Exception as e:
        print(f"ERROR in reset_system: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/settlements")
async def get_superadmin_settlements(db=Depends(get_db)):
    try:
        res = db.table("superadmin_settlements").select("*").order("created_at", desc=True).execute()
        return res.data
    except Exception as e:
        print(f"ERROR in get_superadmin_settlements: {e}")
        raise HTTPException(status_code=500, detail=str(e))
