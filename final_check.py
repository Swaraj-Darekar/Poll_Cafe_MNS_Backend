from database import get_db

db = get_db()
s_res = db.table("settlements").select("*").order("created_at", desc=True).limit(5).execute()
print(f"Settlement Count (recent): {len(s_res.data)}")
for s in s_res.data:
    print(f"Settlement ID: {s.get('id')}, Date: {s.get('created_at')}, Total Revenue: {s.get('total_revenue')}")

sess_res = db.table("sessions").select("id, end_time, total_amount").eq("payment_status", "paid").order("end_time", desc=True).limit(5).execute()
print(f"\nSession Count (recent): {len(sess_res.data)}")
for s in sess_res.data:
    print(f"Session ID: {s.get('id')}, End Time: {s.get('end_time')}, Amount: {s.get('total_amount')}")
