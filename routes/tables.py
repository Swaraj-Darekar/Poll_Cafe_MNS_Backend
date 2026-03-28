from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from database import get_db

router = APIRouter(prefix="/tables", tags=["tables"])

class TableStatusUpdate(BaseModel):
    status: str

@router.get("/")
async def get_tables(db=Depends(get_db)):
    response = db.table("tables").select("*").order("table_number").execute()
    return response.data

@router.put("/{table_id}")
async def update_table_status(table_id: int, update: TableStatusUpdate, db=Depends(get_db)):
    response = db.table("tables").update({"status": update.status}).eq("id", table_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Table not found")
    return response.data[0]
