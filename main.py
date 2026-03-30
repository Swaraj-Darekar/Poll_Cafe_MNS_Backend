from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from database import get_db
from routes import settings, tables, sessions, analytics, bookings, superadmin, expenses, menu

app = FastAPI(title="Pool Cafe Management API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with specific frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(settings.router)
app.include_router(tables.router)
app.include_router(sessions.router)
app.include_router(analytics.router)
app.include_router(bookings.router)
app.include_router(superadmin.router)
app.include_router(expenses.router)
app.include_router(menu.router)

@app.get("/")
async def root():
    return {"message": "Pool Cafe Backend is running!"}

@app.get("/test-db")
async def test_db(db=Depends(get_db)):
    try:
        # Check if we can reach Supabase
        response = db.table("tables").select("count", count="exact").execute()
        return {"status": "success", "message": "Supabase connection established!", "table_count": response.count}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
