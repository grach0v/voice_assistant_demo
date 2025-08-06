from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import datetime
# import sqlite3
import os
import json
from retell import Retell

from .models import VerifyRequest, UpdateDateRequest, FinishCallRequest
from .email_tools import send_confirmation_email

# Load environment variables from .env file if it exists (for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, rely on environment variables (Docker case)
    pass

# conn = sqlite3.connect("app.db", check_same_thread=False)
app = FastAPI()

# Get API key from environment variables
api_key = os.environ.get("RETELL_API_KEY")
if not api_key:
    raise ValueError("RETELL_API_KEY environment variable is required")

print("Using Retell API key:", api_key)
retell = Retell(api_key=api_key)


def load_data():
    """Load data from JSON file"""
    with open("data.json", "r") as f:
        return json.load(f)

def save_data(data):
    """Save data to JSON file"""
    with open("data.json", "w") as f:
        json.dump(data, f, indent=2)


def find_package_by_tracking_id(tracking_id):
    """Find package by tracking ID"""
    data = load_data()
    for pkg in data["packages"]:
        if pkg["tracking_id"] == tracking_id:
            return pkg
    return None


def update_package_schedule(tracking_id, new_date):
    """Update package scheduled date"""
    data = load_data()
    for pkg in data["packages"]:
        if pkg["tracking_id"] == tracking_id:
            pkg["scheduled_at"] = new_date
            save_data(data)
            return True
    return False


def add_call_log(tracking_id, transcript, completed=1, escalated=0):
    """Add a new call log entry"""
    data = load_data()
    new_id = max([log.get("id", 0) for log in data["call_logs"]], default=0) + 1
    new_log = {
        "id": new_id,
        "tracking_id": tracking_id,
        "transcript": transcript,
        "completed": completed,
        "escalated": escalated,
        "created_at": datetime.datetime.now().isoformat(timespec="seconds")
    }
    data["call_logs"].append(new_log)
    save_data(data)


def update_call_logs_completed(tracking_id):
    """Mark all incomplete call logs for tracking_id as completed"""
    data = load_data()
    for log in data["call_logs"]:
        if log["tracking_id"] == tracking_id and log["completed"] == 0:
            log["completed"] = 1
    save_data(data)


def get_available_dates():
    """Generate available delivery time slots"""
    now = datetime.datetime.now()
    tomorrow = now + datetime.timedelta(days=1)
    tomorrow_date = tomorrow.strftime("%Y-%m-%d")
    window1 = f"{tomorrow_date} Morning"    # Tomorrow AM slot
    window2 = f"{tomorrow_date} Afternoon"  # Tomorrow PM slot
    # Find next Saturday from today
    days_ahead = (5 - now.weekday()) % 7  # 5 = Saturday (if today is Saturday, this gives 0)
    if days_ahead == 0: 
        days_ahead = 7  # if today is Saturday, use next week's Saturday
    saturday = now + datetime.timedelta(days=days_ahead)
    sat_date = saturday.strftime("%Y-%m-%d")
    window3 = f"{sat_date} Morning"        # Upcoming Saturday AM slot
    return [window1, window2, window3]


def verify_retell_signature(post_data: dict, signature: str) -> bool:
    """Verify the Retell webhook signature"""
    return retell.verify(
        json.dumps(post_data, separators=(",", ":"), ensure_ascii=False),
        api_key=api_key,
        signature=str(signature),
    )

@app.post("/verify")
async def verify(request: Request):
    post_data = await request.json()
    
    # Verify signature
    if not verify_retell_signature(post_data, request.headers.get("X-Retell-Signature")):
        return JSONResponse(status_code=403, content={"status": "error", "message": "Invalid signature"})
    
    # Extract from the nested structure based on the error details
    args = post_data.get("args", {})
    
    # Validate data with Pydantic
    try:
        verify_request = VerifyRequest(
            tracking_id=args.get("tracking_id"),
            postal_code=args.get("postal_code")
        )
    except Exception:
        return {
            "status": "error", 
            "action": "escalate", 
            "message": "Invalid request data. Escalating to a human agent."
        }
    
    # Look up the package by tracking_id
    # cur = conn.cursor()
    # cur.execute("SELECT tracking_id, customer_name, postal_code, email, status FROM packages WHERE tracking_id=?", (verify_request.tracking_id,))
    # pkg = cur.fetchone()
    
    pkg = find_package_by_tracking_id(verify_request.tracking_id)
    
    if not pkg or verify_request.postal_code != pkg["postal_code"]:
        return {
            "status": "error", 
            "action": "escalate", 
            "message": "Could not verify package. Escalating to a human agent."
        }

    status = pkg["status"]
    if status not in ("Out for Delivery", "Scheduled"):
        return {
            "status": "error", 
            "action": "escalate", 
            "message": "Package not eligible for rescheduling. Escalating to a human agent."
        }

    available_windows = get_available_dates()

    return {
        "status": "ok",
        "action": "reschedule",
        "message": available_windows
    }

@app.post("/update_date")
async def update_date(request: Request):
    post_data = await request.json()
    
    # Verify signature
    if not verify_retell_signature(post_data, request.headers.get("X-Retell-Signature")):
        return JSONResponse(status_code=403, content={"status": "error", "message": "Invalid signature"})
    
    # Extract from the nested structure
    args = post_data.get("args", {})
    
    # Validate data with Pydantic
    update_request = UpdateDateRequest(
        tracking_id=args.get("tracking_id"),
        new_date=args.get("new_date")
    )

    # cur = conn.cursor()
    # cur.execute("UPDATE packages SET scheduled_at=? WHERE tracking_id=?", (update_request.new_date, update_request.tracking_id))
    # if cur.rowcount == 0:
    #     return {"status": "error", "message": "Package not found or not eligible for rescheduling."}
    # conn.commit()
    
    success = update_package_schedule(update_request.tracking_id, update_request.new_date)
    if not success:
        return {"status": "error", "message": "Package not found or not eligible for rescheduling."}
    
    return {"status": "ok", "message": f"Package {update_request.tracking_id} rescheduled to {update_request.new_date}."}

@app.post("/finish_call")
async def finish_call(request: Request):
    post_data = await request.json()
    
    if not verify_retell_signature(post_data, request.headers.get("X-Retell-Signature")):
        return JSONResponse(status_code=403, content={"status": "error", "message": "Invalid signature"})
    
    transcript = post_data['call']['transcript']
    tracking_id = post_data['args']['tracking_id']
    
    # Validate data with Pydantic
    finish_request = FinishCallRequest(tracking_id=tracking_id)
    # cur = conn.cursor()
    
    # Get customer email from database
    # cur.execute("SELECT customer_name, email FROM packages WHERE tracking_id=?", (finish_request.tracking_id,))
    # customer_data = cur.fetchone()
    
    pkg = find_package_by_tracking_id(finish_request.tracking_id)
    
    if not pkg:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Package not found"})
    
    customer_name = pkg["customer_name"]
    customer_email = pkg["email"]
    
    # Log the transcript to the database
    # cur.execute(
    #     "INSERT INTO call_logs (tracking_id, transcript, completed, escalated, created_at) VALUES (?, ?, ?, ?, ?)",
    #     (finish_request.tracking_id, transcript, 1, 0, datetime.datetime.now().isoformat(timespec="seconds"))
    # )
    # 
    # # Update any existing incomplete call logs for this tracking_id
    # cur.execute("UPDATE call_logs SET completed=1 WHERE tracking_id=? AND completed=0", (finish_request.tracking_id,))
    # 
    # conn.commit()
    
    # Add call log and update existing incomplete logs
    add_call_log(finish_request.tracking_id, transcript, completed=1, escalated=0)
    update_call_logs_completed(finish_request.tracking_id)

    # Send a confirmation email to the customer
    send_confirmation_email(finish_request.tracking_id, customer_name, customer_email, transcript)
    
    return {"status": "ok", "message": f"Call for package {finish_request.tracking_id} finished and transcript logged."}
