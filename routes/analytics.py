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
        # Define IST (UTC+5:30) as business context
        IST = timezone(timedelta(hours=5, minutes=30))
        now_ist = datetime.now(IST)
        
        # 0. Calculate Business Today Start (4:30 AM local)
        if now_ist.hour < 4 or (now_ist.hour == 4 and now_ist.minute < 30):
            # If before 4:30 AM, business today started at 4:30 AM yesterday
            biz_today_start_ist = (now_ist - timedelta(days=1)).replace(hour=4, minute=30, second=0, microsecond=0)
        else:
            # If after 4:30 AM, business today started at 4:30 AM today
            biz_today_start_ist = now_ist.replace(hour=4, minute=30, second=0, microsecond=0)
            
        # Convert back to UTC for database queries
        today_start = biz_today_start_ist.astimezone(timezone.utc)
        yesterday_start = today_start - timedelta(days=1)
        yesterday_end = today_start
        
        # 1. Find latest settlement date for "Cycle Start"

        latest_settlement = db.table("settlements")\
            .select("created_at")\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        if latest_settlement.data:
            cycle_start = datetime.fromisoformat(latest_settlement.data[0]["created_at"].replace('Z', '+00:00'))
        else:
            cycle_start = (now_ist.replace(day=1, hour=0, minute=0, second=0, microsecond=0)).astimezone(timezone.utc)

        # 2. Fetch Business Today's Paid Data (since 4:30 AM OR last settlement, whichever is later)
        # This ensures that after a settlement, today's sales resets to 0
        effective_today_start = max(today_start, cycle_start)
        
        # 1. Fetch Effective Today's Paid Sessions (Session Balances)
        # Select * to gracefully handle payment_method if it exists
        today_sessions = db.table("sessions")\
            .select("*")\
            .eq("payment_status", "paid")\
            .gte("end_time", effective_today_start.isoformat())\
            .execute()
        
        # 1.1 Fetch Today's Paid Bookings (Advances)
        # Assuming bookings advance_paid is usually online, but we can default it to online.
        today_bookings = db.table("bookings")\
            .select("*")\
            .eq("payment_status", "paid")\
            .gte("created_at", effective_today_start.isoformat())\
            .execute()
        
        # 3. Fetch Business Yesterday's Paid Data (4:30 AM prev to 4:30 AM today)
        yesterday_sessions = db.table("sessions")\
            .select("*")\
            .eq("payment_status", "paid")\
            .gte("end_time", yesterday_start.isoformat())\
            .lt("end_time", yesterday_end.isoformat())\
            .execute()
            
        yesterday_bookings = db.table("bookings")\
            .select("*")\
            .eq("payment_status", "paid")\
            .gte("created_at", yesterday_start.isoformat())\
            .lt("created_at", yesterday_end.isoformat())\
            .execute()

        # 4. Fetch "Current Cycle" Paid Data (Since last settlement)
        # Note: We filter cycle_sessions by (max of cycle_start and today_start or just cycle_start?)
        # Cycle should be total since settlement.
        cycle_sessions = db.table("sessions")\
            .select("*")\
            .eq("payment_status", "paid")\
            .gte("end_time", cycle_start.isoformat())\
            .execute()
            
        cycle_bookings = db.table("bookings")\
            .select("*")\
            .eq("payment_status", "paid")\
            .gte("created_at", cycle_start.isoformat())\
            .execute()

        # Calculation helper
        def aggregate(sessions, bookings):
            revenue = sum(item.get("total_amount", 0) or 0 for item in sessions) + \
                      sum(item.get("advance_paid", 0) or 0 for item in bookings)
            
            # Separate table sessions from takeaway sessions
            table_sessions = [s for s in sessions if s.get("table_id") is not None]
            takeaway_sessions = [s for s in sessions if s.get("table_id") is None]
            
            table_bookings_count = len(table_sessions) + len(bookings)
            takeaway_count = len(takeaway_sessions)
            
            # Calculate payment method breakdown
            cash_total = sum(item.get("total_amount", 0) or 0 for item in sessions if item.get("payment_method") == "cash")
            online_total = sum(item.get("total_amount", 0) or 0 for item in sessions if item.get("payment_method", "online") != "cash") + \
                           sum(item.get("advance_paid", 0) or 0 for item in bookings) # Assuming bookings are online
            
            # Takeaway revenue breakdown
            takeaway_revenue = sum(item.get("total_amount", 0) or 0 for item in takeaway_sessions)
            table_revenue = revenue - takeaway_revenue
            
            return {
                "revenue": round(revenue, 2), 
                "bookings": table_bookings_count,
                "takeaways": takeaway_count,
                "takeaway_revenue": round(takeaway_revenue, 2),
                "table_revenue": round(table_revenue, 2),
                "cash_total": round(cash_total, 2),
                "online_total": round(online_total, 2)
            }

        return {
            "today": aggregate(today_sessions.data or [], today_bookings.data or []),
            "yesterday": aggregate(yesterday_sessions.data or [], yesterday_bookings.data or []),
            "cycle": aggregate(cycle_sessions.data or [], cycle_bookings.data or []),
            "cycle_start": cycle_start.isoformat(),
            "business_today_start": today_start.isoformat()
        }

    except Exception as e:
        print(f"ERROR: Analytics fetch failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analytics failed: {str(e)}")

@router.get("/history")
async def get_session_history(db=Depends(get_db)):
    """Return all paid sessions since last settlement, grouped by business day (4:30 AM IST cutoff)."""
    try:
        IST = timezone(timedelta(hours=5, minutes=30))
        now_ist = datetime.now(IST)
        
        # Find cycle start (last settlement)
        latest_settlement = db.table("settlements")\
            .select("created_at")\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        if latest_settlement.data:
            cycle_start = datetime.fromisoformat(latest_settlement.data[0]["created_at"].replace('Z', '+00:00'))
        else:
            cycle_start = (now_ist.replace(day=1, hour=0, minute=0, second=0, microsecond=0)).astimezone(timezone.utc)
        
        # Fetch all paid sessions since cycle start, with table info
        sessions_response = db.table("sessions")\
            .select("*, tables(table_number, type)")\
            .eq("payment_status", "paid")\
            .gte("end_time", cycle_start.isoformat())\
            .order("end_time", desc=True)\
            .execute()
        
        sessions = sessions_response.data or []
        
        # Group sessions by business day (4:30 AM IST cutoff)
        # A business day runs from 4:30 AM to next day 4:30 AM
        days = {}
        for s in sessions:
            end_time_str = s.get("end_time")
            if not end_time_str:
                continue
            
            end_time_utc = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            end_time_ist = end_time_utc.astimezone(IST)
            
            # Determine business day: if before 4:30 AM, it belongs to previous calendar day
            if end_time_ist.hour < 4 or (end_time_ist.hour == 4 and end_time_ist.minute < 30):
                biz_date = (end_time_ist - timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                biz_date = end_time_ist.strftime("%Y-%m-%d")
            
            # Build session entry
            table_info = s.get("tables")
            is_takeaway = s.get("table_id") is None
            
            if is_takeaway:
                table_name = "Take Away"
                table_type = "takeaway"
            else:
                table_num = table_info.get("table_number", "?") if table_info else "?"
                table_type = table_info.get("type", "small") if table_info else "small"
                if table_type == "big":
                    table_name = f"Big Table {table_num}"
                elif table_type == "sd" or str(table_num) == "5":
                    table_name = "SD Gaming Table"
                else:
                    table_name = f"Table {table_num}"
            
            entry = {
                "id": s.get("id"),
                "table_name": table_name,
                "table_type": table_type,
                "is_takeaway": is_takeaway,
                "customer_name": s.get("customer_name", ""),
                "total_minutes": s.get("total_minutes", 0) or 0,
                "total_amount": s.get("total_amount", 0) or 0,
                "gross_amount": s.get("gross_amount", 0) or 0,
                "commission_amount": s.get("commission_amount", 0) or 0,
                "payment_method": s.get("payment_method", "online"),
                "end_time": end_time_ist.strftime("%I:%M %p"),
                "start_time_raw": s.get("start_time", ""),
                "end_time_raw": end_time_str
            }
            
            # Calculate discount if gross > total (discount = gross - total - commission)
            gross = entry["gross_amount"]
            total = entry["total_amount"]
            commission = entry["commission_amount"]
            advance = s.get("advance_amount", 0) or 0
            discount = max(0, gross + commission - advance - total) if not is_takeaway else 0
            entry["discount"] = round(discount, 2)
            
            if biz_date not in days:
                days[biz_date] = []
            days[biz_date].append(entry)
        
        # Convert to sorted list of day groups
        today_date = now_ist.strftime("%Y-%m-%d")
        if now_ist.hour < 4 or (now_ist.hour == 4 and now_ist.minute < 30):
            today_date = (now_ist - timedelta(days=1)).strftime("%Y-%m-%d")
        
        yesterday_date_obj = datetime.strptime(today_date, "%Y-%m-%d") - timedelta(days=1)
        yesterday_date = yesterday_date_obj.strftime("%Y-%m-%d")
        
        result = []
        for date_str in sorted(days.keys(), reverse=True):
            day_sessions = days[date_str]
            day_total = sum(s["total_amount"] for s in day_sessions)
            table_count = sum(1 for s in day_sessions if not s["is_takeaway"])
            takeaway_count = sum(1 for s in day_sessions if s["is_takeaway"])
            
            if date_str == today_date:
                label = "Today"
            elif date_str == yesterday_date:
                label = "Yesterday"
            else:
                # Format as "Mon, 28 Mar"
                d = datetime.strptime(date_str, "%Y-%m-%d")
                label = d.strftime("%a, %d %b")
            
            result.append({
                "date": date_str,
                "label": label,
                "sessions": day_sessions,
                "day_total": round(day_total, 2),
                "table_count": table_count,
                "takeaway_count": takeaway_count
            })
        
        return result
    
    except Exception as e:
        print(f"ERROR: History fetch failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"History failed: {str(e)}")

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
        
        # 1.1 Snapshot current cycle expenses
        cycle_start_iso = analytics["cycle_start"]
        # Include a 5-second buffer to capture expenses created at the very same moment
        snapshot_end_iso = (datetime.now(timezone.utc) + timedelta(seconds=5)).isoformat()
        
        expenses_response = db.table("expenses")\
            .select("*")\
            .gte("created_at", cycle_start_iso)\
            .lte("created_at", snapshot_end_iso)\
            .order("created_at", desc=False)\
            .execute()
        
        expense_list = expenses_response.data or []

        
        # 2. Save to settlements table
        settlement_data = {
            "month": data.month,
            "year": data.year,
            "total_revenue": revenue,
            "total_expense": expense,
            "profit_loss": profit,
            "expense_details": expense_list,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        try:
            # Primary Save with expense snapshot
            response = db.table("settlements").insert(settlement_data).execute()
        except Exception as e:
            print(f"DEBUG: Save with expense_details failed (likely missing column): {e}")
            # Fallback Save (No snapshot, requires running SQL migration)
            fallback_data = {k: v for k, v in settlement_data.items() if k != "expense_details"}
            response = db.table("settlements").insert(fallback_data).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to save settlement")
            
        return {"message": "Month settled successfully", "settlement": response.data[0]}
    except Exception as e:
        print(f"ERROR: Settlement failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Settlement failed: {str(e)}")
