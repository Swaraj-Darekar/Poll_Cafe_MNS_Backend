from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from database import get_db
from typing import List, Optional

router = APIRouter(prefix="/menu", tags=["menu"])

class MenuItem(BaseModel):
    name: str
    price: float
    category: Optional[str] = "Others"

class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None

@router.get("/")
async def get_menu(db=Depends(get_db)):
    try:
        response = db.table("menu").select("*").order("name").execute()
        return response.data
    except Exception as e:
        print(f"Error fetching menu: {e}")
        # Standard default menu if table is missing or empty
        return [
            {"id": 1, "name": "Cold Drink (250ml)", "price": 25, "category": "Drinks"},
            {"id": 2, "name": "Water Bottle (1L)", "price": 20, "category": "Drinks"},
            {"id": 3, "name": "Soda (600ml)", "price": 40, "category": "Drinks"},
            {"id": 4, "name": "Snacks (Large)", "price": 50, "category": "Snacks"},
            {"id": 5, "name": "Tea / Coffee", "price": 15, "category": "Drinks"}
        ]

@router.post("/")
async def add_menu_item(item: MenuItem, db=Depends(get_db)):
    try:
        response = db.table("menu").insert({
            "name": item.name,
            "price": item.price,
            "category": item.category
        }).execute()
        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to add menu item")
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{item_id}")
async def update_menu_item(item_id: int, item: MenuItemUpdate, db=Depends(get_db)):
    try:
        update_data = {}
        if item.name is not None: update_data["name"] = item.name
        if item.price is not None: update_data["price"] = item.price
        if item.category is not None: update_data["category"] = item.category
        
        response = db.table("menu").update(update_data).eq("id", item_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Item not found")
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{item_id}")
async def delete_menu_item(item_id: int, db=Depends(get_db)):
    try:
        response = db.table("menu").delete().eq("id", item_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"message": "Item deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
