from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from database import get_db
from typing import Optional

router = APIRouter(prefix="/bookings", tags=["bookings"])

class BookingRequest(BaseModel):
    table_type: str  # "big" or "small"
    name: str
    phone: str
    booking_time: str  # ISO string
    duration: Optional[int] = 1

@router.post("/check-availability")
async def check_availability(data: dict, db=Depends(get_db)):
    try:
        search_time = datetime.fromisoformat(data["booking_time"].replace("Z", "+00:00"))
        duration = int(data.get("duration", 1))
        end_time = search_time + timedelta(hours=duration)

        # 1. Get all tables grouped by type
        tables_res = db.table("tables").select("*").execute()
        all_tables = tables_res.data

        # 2. Get overlapping confirmed bookings
        # Duration might not exist as a column yet, so we select what we know
        bookings_res = db.table("bookings")\
            .select("table_id, booking_time")\
            .in_("status", ["confirmed", "pending_admin"])\
            .execute()

        unavailable_table_ids = set()
        for b in bookings_res.data:
            b_start = datetime.fromisoformat(b["booking_time"].replace("Z", "+00:00"))
            # Use duration from row if exists, else default 1.5h
            b_dur = b.get("duration", 1.5) 
            b_end = b_start + timedelta(hours=b_dur)
            if search_time < b_end and end_time > b_start:
                unavailable_table_ids.add(b["table_id"])

        # 3. Check active sessions if search_time is close to now
        now = datetime.now(timezone.utc)
        if search_time < now + timedelta(minutes=30):
            # Active sessions use end_time IS NULL
            sessions_res = db.table("sessions").select("table_id").is_("end_time", "null").execute()
            for s in sessions_res.data:
                unavailable_table_ids.add(s["table_id"])

        # Fetch dynamic settings for table pricing
        settings_res = db.table("settings").select("*").order("updated_at", desc=True).limit(1).execute()
        settings_data = settings_res.data[0] if settings_res.data else {}
        small_price = settings_data.get("small_price_per_hour") or settings_data.get("price_per_hour_small") or settings_data.get("price_per_hour", 100)
        big_price = settings_data.get("big_price_per_hour") or settings_data.get("price_per_hour_big", 150)

        # 4. Group by type and count
        result = {}
        for t in all_tables:
            ttype = t["type"]
            if ttype not in result:
                result[ttype] = {"total": 0, "available": 0, "price": 0}
            result[ttype]["total"] += 1
            result[ttype]["price"] = big_price if ttype == "big" else small_price
            if t["id"] not in unavailable_table_ids:
                result[ttype]["available"] += 1

        return result
    except Exception as e:
        # Keep detailed error for debugging if needed, but return empty on failure
        print(f"ERROR in check_availability: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/book-table")
async def book_table(data: BookingRequest, db=Depends(get_db)):
    try:
        search_time = datetime.fromisoformat(data.booking_time.replace("Z", "+00:00"))
        duration = data.duration or 1
        end_time = search_time + timedelta(hours=duration)

        # 1. Find a free table of the requested type
        tables_res = db.table("tables").select("*").eq("type", data.table_type).execute()
        all_tables = tables_res.data

        # Check existing overlapping bookings
        bookings_res = db.table("bookings")\
            .select("table_id, booking_time")\
            .in_("status", ["confirmed", "pending_admin"])\
            .execute()

        unavailable_table_ids = set()
        for b in bookings_res.data:
            b_start = datetime.fromisoformat(b["booking_time"].replace("Z", "+00:00"))
            b_dur = b.get("duration", 1.5)
            b_end = b_start + timedelta(hours=b_dur)
            if search_time < b_end and end_time > b_start:
                unavailable_table_ids.add(b["table_id"])

        # Check active sessions
        now = datetime.now(timezone.utc)
        if search_time < now + timedelta(minutes=30):
            sessions_res = db.table("sessions").select("table_id").is_("end_time", "null").execute()
            for s in sessions_res.data:
                unavailable_table_ids.add(s["table_id"])

        free_tables = [t for t in all_tables if t["id"] not in unavailable_table_ids]

        if not free_tables:
            raise HTTPException(status_code=400, detail="No tables available for this time slot.")

        assigned_table = free_tables[0]

        booking_data = {
            "table_id": assigned_table["id"],
            "name": data.name,
            "phone": data.phone,
            "booking_time": search_time.isoformat(),
            "advance_paid": 100.0,
            "payment_status": "paid",
            "status": "pending_admin",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        response = db.table("bookings").insert(booking_data).execute()
        return response.data[0]
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"ERROR in book_table: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending-notifications")
async def get_pending_notifications(db=Depends(get_db)):
    try:
        response = db.table("bookings")\
            .select("*, tables(table_number, type)")\
            .eq("status", "pending_admin")\
            .order("created_at", desc=True)\
            .execute()
        return response.data
    except Exception as e:
        print(f"INFO: pending-notifications skipped (bookings table may not exist): {e}")
        return []  # Graceful empty return — do not crash


@router.post("/{booking_id}/approve")
async def approve_booking(booking_id: int, db=Depends(get_db)):
    try:
        response = db.table("bookings")\
            .update({"status": "confirmed"})\
            .eq("id", booking_id)\
            .execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Booking not found")
        return response.data[0]
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{booking_id}/reject")
async def reject_booking(booking_id: int, db=Depends(get_db)):
    try:
        response = db.table("bookings")\
            .update({"status": "payment_failed"})\
            .eq("id", booking_id)\
            .execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Booking not found")
        return response.data[0]
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{booking_id}")
async def get_booking_status(booking_id: int, db=Depends(get_db)):
    try:
        response = db.table("bookings")\
            .select("id, status, name, booking_time")\
            .eq("id", booking_id)\
            .execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Booking not found")
        return response.data[0]
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-phone/{phone}")
async def get_booking_by_phone(phone: str, db=Depends(get_db)):
    try:
        response = db.table("bookings")\
            .select("*")\
            .eq("phone", phone)\
            .in_("status", ["confirmed", "pending_admin"])\
            .order("booking_time", desc=False)\
            .limit(1)\
            .execute()
        return response.data[0] if response.data else None
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/available-tables")
async def get_available_tables(db=Depends(get_db)):
    try:
        tables_response = db.table("tables").select("*").eq("status", "available").execute()
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=2)
        bookings_response = db.table("bookings")\
            .select("table_id")\
            .in_("status", ["confirmed", "pending_admin"])\
            .gte("booking_time", now.isoformat())\
            .lte("booking_time", future.isoformat())\
            .execute()
        booked_table_ids = [b["table_id"] for b in bookings_response.data]
        available_tables = [t for t in tables_response.data if t["id"] not in booked_table_ids]
        return available_tables
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all")
async def get_all_bookings(db=Depends(get_db)):
    try:
        response = db.table("bookings")\
            .select("*, tables(table_number, type)")\
            .order("booking_time", desc=True)\
            .execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history")
async def clear_booking_history(db=Depends(get_db)):
    try:
        # 1. First find all bookings that would be deleted
        bookings_to_delete = db.table("bookings")\
            .select("id")\
            .not_.in_("status", ["confirmed", "pending_admin"])\
            .execute()
        
        if not bookings_to_delete.data:
            return {"message": "No history records to clear"}
            
        booking_ids = [b["id"] for b in bookings_to_delete.data]
        
        # 2. Update sessions table to set booking_id to NULL for these bookings
        # to avoid foreign key constraint violations
        db.table("sessions")\
            .update({"booking_id": None})\
            .in_("booking_id", booking_ids)\
            .execute()

        # 3. Now delete the bookings
        response = db.table("bookings")\
            .delete()\
            .in_("id", booking_ids)\
            .execute()
            
        return {"message": f"Cleared {len(response.data)} history records"}
    except Exception as e:
        print(f"ERROR: Clear history failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upcoming-per-table")
async def get_upcoming_per_table(db=Depends(get_db)):
    try:
        now = datetime.now(timezone.utc)
        # End of today
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        response = db.table("bookings")\
            .select("*")\
            .in_("status", ["confirmed", "pending_admin"])\
            .gte("booking_time", now.isoformat())\
            .lte("booking_time", end_of_day.isoformat())\
            .order("booking_time", desc=False)\
            .execute()
            
        # Group by table_id and take the first one (earliest)
        bookings = response.data
        next_bookings = {}
        for b in bookings:
            tid = b["table_id"]
            if tid not in next_bookings:
                next_bookings[tid] = b
                
        return next_bookings
    except Exception as e:
        print(f"INFO: upcoming-per-table skipped (bookings table may not exist): {e}")
        return {}  # Graceful empty return — do not crash
