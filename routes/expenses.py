from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone
from database import get_db
from typing import Optional

router = APIRouter(prefix="/expenses", tags=["expenses"])

class ExpenseRequest(BaseModel):
    name: str
    amount: float
    date: str # ISO string or YYYY-MM-DD

@router.get("/")
async def get_current_cycle_expenses(db=Depends(get_db)):
    try:
        now = datetime.now(timezone.utc)
        
        # Determine Cycle Start from settlements table
        latest_settlement = db.table("settlements")\
            .select("created_at")\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        if latest_settlement.data:
            cycle_start = datetime.fromisoformat(latest_settlement.data[0]["created_at"].replace('Z', '+00:00'))
        else:
            # No settlement yet — include ALL expenses since the beginning
            cycle_start = datetime(2000, 1, 1, tzinfo=timezone.utc)

        # Fetch expenses AFTER cycle_start
        response = db.table("expenses")\
            .select("*")\
            .gte("created_at", cycle_start.isoformat())\
            .order("created_at", desc=False)\
            .execute()
            
        return response.data or []
    except Exception as e:
        print(f"ERROR fetching expenses: {e}")
        # Return empty array if the table doesn't exist yet
        return []

@router.get("/history")
async def get_expenses_in_range(start_date: str, end_date: str, db=Depends(get_db)):
    try:
        # Fetch expenses BETWEEN start_date and end_date
        response = db.table("expenses")\
            .select("*")\
            .gte("created_at", start_date)\
            .lte("created_at", end_date)\
            .order("created_at", desc=False)\
            .execute()
            
        return response.data or []
    except Exception as e:
        print(f"ERROR fetching historical expenses: {e}")
        return []


@router.post("/")
async def add_expense(data: ExpenseRequest, db=Depends(get_db)):
    try:
        # We also manually insert created_at to avoid timezone issues or if the column defaults aren't precise
        new_expense = {
            "name": data.name,
            "amount": data.amount,
            "date": data.date,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        response = db.table("expenses").insert(new_expense).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to insert expense")
            
        return response.data[0]
    except Exception as e:
        print(f"ERROR adding expense: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{expense_id}")
async def delete_expense(expense_id: int, db=Depends(get_db)):
    try:
        response = db.table("expenses").delete().eq("id", expense_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Expense not found or already deleted")
        return {"success": True}
    except Exception as e:
        print(f"ERROR deleting expense: {e}")
        raise HTTPException(status_code=500, detail=str(e))
