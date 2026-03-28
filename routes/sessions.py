from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone
from database import get_db
from typing import Optional
from cachetools import TTLCache

router = APIRouter(tags=["sessions"])

settings_cache = TTLCache(maxsize=5, ttl=300)

def get_cached_settings(db):
    if "latest" in settings_cache:
        return settings_cache["latest"]
    settings = db.table("settings").select("*").order("updated_at", desc=True).limit(1).execute()
    if settings.data:
        settings_cache["latest"] = settings.data
    return settings.data

class SessionStart(BaseModel):
    table_id: int
    customer_name: str
    customer_phone: str
    booking_id: Optional[int] = None

class SessionEnd(BaseModel):
    session_id: int
    is_preview: bool = False

class SessionPay(BaseModel):
    total_amount: float
    gross_amount: float
    commission_amount: float
    duration_minutes: int
    payment_method: str = "online"

@router.post("/start-table")
async def start_session(data: SessionStart, db=Depends(get_db)):
    print(f"DEBUG: Starting table {data.table_id} for {data.customer_name}")
    # 1. Check if table is available
    table = db.table("tables").select("status").eq("id", data.table_id).execute()
    if not table.data or table.data[0]["status"] != "available":
        raise HTTPException(status_code=400, detail="Table is not available")

    advance_amount = 0
    if data.booking_id:
        # Check booking
        booking = db.table("bookings").select("*").eq("id", data.booking_id).execute()
        if booking.data:
            advance_amount = booking.data[0].get("advance_paid", 0)
            # Mark booking as completed
            db.table("bookings").update({"status": "completed"}).eq("id", data.booking_id).execute()

    # 2. Create session
    session_data = {
        "table_id": data.table_id,
        "customer_name": data.customer_name,
        "customer_phone": data.customer_phone,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "payment_status": "pending",
        "booking_id": data.booking_id,
        "advance_amount": advance_amount
    }
    session_response = db.table("sessions").insert(session_data).execute()
    if not session_response.data:
        raise HTTPException(status_code=500, detail="Failed to create session")

    # 3. Update table status
    db.table("tables").update({"status": "occupied"}).eq("id", data.table_id).execute()

    print(f"DEBUG: Session created with ID: {session_response.data[0]['id']}")
    return session_response.data[0]

@router.post("/end-table")
async def end_session(data: SessionEnd, db=Depends(get_db)):
    print(f"DEBUG: Ending session {data.session_id}")
    # 1. Fetch session and table info
    session = db.table("sessions").select("*, tables(*)").eq("id", data.session_id).execute()
    if not session.data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    current_session = session.data[0]
    start_time = datetime.fromisoformat(current_session["start_time"].replace('Z', '+00:00'))
    end_time = datetime.now(timezone.utc)
    
    # 2. Calculate duration
    duration = end_time - start_time
    total_minutes = int(duration.total_seconds() / 60)
    
    # 3. Fetch price from settings
    settings_data = get_cached_settings(db)
    
    # Helper to get setting safely
    def get_setting(key, default):
        if settings_data and len(settings_data) > 0:
            return settings_data[0].get(key, default)
        return default

    table_type = current_session["tables"]["type"]
    if table_type == "big":
        price_per_hour = get_setting("big_price_per_hour", 150)
    else:
        # Fallback to old price_per_hour if small_price_per_hour is missing
        price_per_hour = get_setting("small_price_per_hour", get_setting("price_per_hour_small", get_setting("price_per_hour", 100)))
        
    upi_id = get_setting("upi_id", "example@upi")

    # 4. Calculate total amount
    # total_amount = (minutes / 60) * price_per_hour
    gross_amount = int(round((duration.total_seconds() / 3600) * float(price_per_hour)))
    
    # 4.1 Handle Commission (Add to Bill)
    is_commission_enabled = get_setting("is_commission_enabled", False)
    commission_amount = float(get_setting("commission_per_booking", 5.0)) if is_commission_enabled else 0.0
    
    # DEDUCT ADVANCE
    advance_already_paid = current_session.get("advance_amount", 0) or 0
    total_amount = int(round(max(0, gross_amount + commission_amount - float(advance_already_paid))))

    # 5. Update session (ONLY if not preview)
    session_obj = {}
    if not data.is_preview:
        update_data = {
            "end_time": end_time.isoformat(),
            "total_minutes": total_minutes,
            "total_amount": total_amount,
            "commission_amount": commission_amount # Store it for history
        }
        
        try:
            session_update = db.table("sessions").update(update_data).eq("id", data.session_id).execute()
        except Exception as e:
            print(f"DEBUG: Session update with commission_amount failed (likely missing column): {e}")
            # Fallback to updating without commission_amount
            fallback_data = {
                "end_time": end_time.isoformat(),
                "total_minutes": total_minutes,
                "total_amount": total_amount
            }
            session_update = db.table("sessions").update(fallback_data).eq("id", data.session_id).execute()
            
        if session_update.data:
            session_obj = session_update.data[0]
            
        # 6. Update table status to available
        try:
            db.table("tables").update({"status": "available"}).eq("id", current_session["table_id"]).execute()
        except: pass
    else:
        # For preview, just use the current session data but with updated values for the UI
        session_obj = {**current_session, "total_amount": total_amount, "total_minutes": total_minutes}

    # 7. Prepare response (Robustly)
    if data.is_preview:
        # Construct preview session object
        session_obj = {
            **current_session,
            "end_time": end_time.isoformat(),
            "total_minutes": total_minutes,
            "total_amount": total_amount,
            "gross_amount": gross_amount,
            "advance_amount": advance_already_paid,
            "commission_amount": commission_amount,
            "upi_id": upi_id,
            "rate": price_per_hour
        }
    else:
        # Use updated session from DB if available
        if 'session_update' in locals() and session_update.data:
            session_obj = session_update.data[0]
            session_obj["gross_amount"] = gross_amount
            session_obj["advance_amount"] = advance_already_paid
            session_obj["commission_amount"] = commission_amount
            session_obj["upi_id"] = upi_id
            session_obj["rate"] = price_per_hour
        else:
            session_obj = {
                **current_session,
                "end_time": end_time.isoformat(),
                "total_minutes": total_minutes,
                "total_amount": total_amount,
                "gross_amount": gross_amount,
                "advance_amount": advance_already_paid,
                "commission_amount": commission_amount,
                "upi_id": upi_id,
                "rate": price_per_hour
            }

    print(f"DEBUG: Session {data.session_id} ended. Gross: {gross_amount}, Comm: {commission_amount}, Advance: {advance_already_paid}, Total: {total_amount}")
    
    return {
        "session": session_obj,
        "total_amount": float(total_amount),
        "gross_amount": float(gross_amount),
        "advance_amount": float(advance_already_paid),
        "commission_amount": float(commission_amount),
        "upi_id": upi_id,
        "total_minutes": int(total_minutes),
        "total_seconds": int(duration.total_seconds()),
        "minutes": int(total_minutes),
        "rate": float(price_per_hour)
    }

@router.get("/active-sessions")
async def get_active_sessions(db=Depends(get_db)):
    # Fetch sessions where end_time is NULL (active)
    response = db.table("sessions").select("*").is_("end_time", "null").execute()
    return response.data

@router.post("/{session_id}/pay")
async def mark_paid(session_id: int, data: SessionPay, db=Depends(get_db)):
    try:
        # 1. Fetch current session to get table_id
        session_query = db.table("sessions").select("table_id").eq("id", session_id).execute()
        table_id = session_query.data[0]["table_id"] if session_query.data else None

        # 2. Permanent Session Closure
        end_time = datetime.now(timezone.utc).isoformat()
        update_data = {
            "payment_status": "paid",
            "end_time": end_time,
            "total_amount": data.total_amount,
            "gross_amount": data.gross_amount,
            "commission_amount": data.commission_amount,
            "total_minutes": data.duration_minutes,
            "payment_method": data.payment_method
        }
        
        # Try updating with all fields
        try:
            response = db.table("sessions").update(update_data).eq("id", session_id).execute()
        except:
            # Fallback if commission_amount or payment_method column is missing
            try:
                fallback_data = {
                    "payment_status": "paid",
                    "end_time": end_time,
                    "total_amount": data.total_amount,
                    "total_minutes": data.duration_minutes,
                    "payment_method": data.payment_method
                }
                response = db.table("sessions").update(fallback_data).eq("id", session_id).execute()
            except:
                # Ultimate fallback
                ultimate_fallback = {
                    "payment_status": "paid",
                    "end_time": end_time,
                    "total_amount": data.total_amount,
                    "total_minutes": data.duration_minutes
                }
                response = db.table("sessions").update(ultimate_fallback).eq("id", session_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # 3. Update table status to available
        if table_id:
            db.table("tables").update({"status": "available"}).eq("id", table_id).execute()

        # 4. Commission Logic: Deduct from Wallet (Mandatory always)
        settings_data = get_cached_settings(db)
        if settings_data:
            sid = settings_data[0]["id"]
            current_balance = float(settings_data[0].get("wallet_balance", 0))
            commission_per_booking = float(settings_data[0].get("commission_per_booking") or 5.0)
            new_balance = current_balance - commission_per_booking
            
            # Update settings
            db.table("settings").update({"wallet_balance": new_balance}).eq("id", sid).execute()
            
            # Log transaction
            db.table("wallet_transactions").insert({
                "type": "debit",
                "amount": commission_per_booking,
                "reason": f"Commission for Session #{session_id}"
            }).execute()
            
            # Invalidate cache since we updated settings
            settings_cache.pop("latest", None)

        return response.data[0]
    except Exception as e:
        # If it fails (e.g. missing columns), we still want the payment to be marked
        # but we should log the error
        print(f"ERROR in mark_paid commission logic: {e}")
        return response.data[0] if 'response' in locals() and response.data else {"id": session_id, "payment_status": "paid"}

