from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from database import get_db

router = APIRouter(prefix="/settings", tags=["settings"])

class SettingsUpdate(BaseModel):
    small_price_per_hour: int
    big_price_per_hour: int
    upi_id: str
    is_commission_enabled: bool = False

@router.get("/")
async def get_settings(db=Depends(get_db)):
    response = db.table("settings").select("*").order("updated_at", desc=True).limit(1).execute()
    if not response.data:
        # Return default if no settings exist
        return {
            "small_price_per_hour": 100, 
            "big_price_per_hour": 150, 
            "upi_id": "example@upi",
            "is_commission_enabled": False
        }
    
    # Ensure missing columns don't break the response
    data = response.data[0]
    return {
        "id": data.get("id"),
        "small_price_per_hour": data.get("small_price_per_hour") or data.get("price_per_hour_small") or data.get("price_per_hour", 100),
        "big_price_per_hour": data.get("big_price_per_hour") or data.get("price_per_hour_big", 150),
        "upi_id": data.get("upi_id", "example@upi"),
        "is_commission_enabled": data.get("is_commission_enabled", False),
        "commission_per_booking": data.get("commission_per_booking", 5.0)
    }

@router.post("/")
async def update_settings(settings: SettingsUpdate, db=Depends(get_db)):
    try:
        # Get the latest settings row or create one
        existing = db.table("settings").select("id").limit(1).execute()
        
        if existing.data:
            row_id = existing.data[0]["id"]
            
            # Initial attempt with full schema
            try:
                response = db.table("settings").update({
                    "small_price_per_hour": settings.small_price_per_hour,
                    "big_price_per_hour": settings.big_price_per_hour,
                    "upi_id": settings.upi_id,
                    "is_commission_enabled": settings.is_commission_enabled,
                    "updated_at": "now()"
                }).eq("id", row_id).execute()
            except Exception as e:
                # Fallback if column is missing (e.g. small_price_per_hour)
                print(f"DEBUG: Update failed (likely missing column): {e}")
                update_payload = {
                    "price_per_hour": settings.small_price_per_hour,
                    "upi_id": settings.upi_id,
                    "is_commission_enabled": settings.is_commission_enabled,
                    "updated_at": "now()"
                }
                response = db.table("settings").update(update_payload).eq("id", row_id).execute()
        else:
            # Insert new row
            response = db.table("settings").insert({
                "small_price_per_hour": settings.small_price_per_hour,
                "big_price_per_hour": settings.big_price_per_hour,
                "upi_id": settings.upi_id,
                "is_commission_enabled": settings.is_commission_enabled
            }).execute()
            
        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to update settings")
        return response.data[0]
    except Exception as e:
        print(f"ERROR: Settings update failed: {str(e)}")
        if "PGRST204" in str(e) or "column" in str(e).lower():
            raise HTTPException(status_code=500, detail="Database schema mismatch. You can save your UPI ID, but Big/Small pricing requires running SQL migration.")
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")
