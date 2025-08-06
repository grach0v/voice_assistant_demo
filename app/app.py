from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import datetime
import sqlite3
import os
import json
from dotenv import load_dotenv
from retell import Retell

import base64
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


class VerifyRequest(BaseModel):
    postal_code: str
    tracking_id: str

class UpdateDateRequest(BaseModel):
    tracking_id: str
    new_date: str

class FinishCallRequest(BaseModel):
    tracking_id: str

conn = sqlite3.connect("app.db", check_same_thread=False)
load_dotenv()  
app = FastAPI()
retell = Retell(api_key=os.environ["RETELL_API_KEY"])

SCOPES = ['https://www.googleapis.com/auth/gmail.send']
def get_gmail_service():
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    return build('gmail', 'v1', credentials=creds)

def create_message(to, subject, body_text):
    message = MIMEText(body_text)
    message['to'] = to
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw}

def send_message(service, user_id, message):
    sent = service.users().messages().send(userId=user_id, body=message).execute()
    print(f"Message sent! ID: {sent['id']}")
    return sent

def get_available_dates():
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

@app.post("/verify")
async def verify(request: Request):
    post_data = await request.json()
    
    # Verify signature
    valid_signature = retell.verify(
        json.dumps(post_data, separators=(",", ":"), ensure_ascii=False),
        api_key=str(os.environ["RETELL_API_KEY"]),
        signature=str(request.headers.get("X-Retell-Signature")),
    )

    if not valid_signature:
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
    cur = conn.cursor()
    cur.execute("SELECT tracking_id, customer_name, postal_code, email, status FROM packages WHERE tracking_id=?", (verify_request.tracking_id,))
    pkg = cur.fetchone()
    
    if not pkg or verify_request.postal_code != pkg[2]:
        return {
            "status": "error", 
            "action": "escalate", 
            "message": "Could not verify package. Escalating to a human agent."
        }

    tracking_id, _, _, _, status = pkg
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
    valid_signature = retell.verify(
        json.dumps(post_data, separators=(",", ":"), ensure_ascii=False),
        api_key=str(os.environ["RETELL_API_KEY"]),
        signature=str(request.headers.get("X-Retell-Signature")),
    )

    if not valid_signature:
        return JSONResponse(status_code=403, content={"status": "error", "message": "Invalid signature"})
    
    # Extract from the nested structure
    args = post_data.get("args", {})
    
    # Validate data with Pydantic
    update_request = UpdateDateRequest(
        tracking_id=args.get("tracking_id"),
        new_date=args.get("new_date")
    )

    cur = conn.cursor()
    cur.execute("UPDATE packages SET scheduled_at=? WHERE tracking_id=?", (update_request.new_date, update_request.tracking_id))
    if cur.rowcount == 0:
        return {"status": "error", "message": "Package not found or not eligible for rescheduling."}

    conn.commit()
    return {"status": "ok", "message": f"Package {update_request.tracking_id} rescheduled to {update_request.new_date}."}

@app.post("/finish_call")
async def finish_call(request: Request):
    post_data = await request.json()
    
    valid_signature = retell.verify(
        json.dumps(post_data, separators=(",", ":"), ensure_ascii=False),
        api_key=str(os.environ["RETELL_API_KEY"]),
        signature=str(request.headers.get("X-Retell-Signature")),
    )

    if not valid_signature:
        return JSONResponse(status_code=403, content={"status": "error", "message": "Invalid signature"})
    
    transcript = post_data['call']['transcript']
    tracking_id = post_data['args']['tracking_id']
    
    # Validate data with Pydantic
    finish_request = FinishCallRequest(tracking_id=tracking_id)
    cur = conn.cursor()
    
    # Get customer email from database
    cur.execute("SELECT customer_name, email FROM packages WHERE tracking_id=?", (finish_request.tracking_id,))
    customer_data = cur.fetchone()
    
    if not customer_data:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Package not found"})
    
    customer_name, customer_email = customer_data
    
    # Log the transcript to the database
    cur.execute(
        "INSERT INTO call_logs (tracking_id, transcript, completed, escalated, created_at) VALUES (?, ?, ?, ?, ?)",
        (finish_request.tracking_id, transcript, 1, 0, datetime.datetime.now().isoformat(timespec="seconds"))
    )
    
    # Update any existing incomplete call logs for this tracking_id
    cur.execute("UPDATE call_logs SET completed=1 WHERE tracking_id=? AND completed=0", (finish_request.tracking_id,))
    
    conn.commit()

    # Send a confirmation email to the customer
    try:
        service = get_gmail_service()
        subject = f"Call Completed - Package {finish_request.tracking_id}"
        body_text = f"Hello {customer_name},\n\nYour call regarding package {finish_request.tracking_id} has been completed.\n\nCall Summary:\n{transcript}\n\nThank you for using our service!"
        message = create_message(customer_email, subject, body_text)
        send_message(service, "me", message)
    except Exception as e:
        print(f"Failed to send email: {e}")
        # Don't fail the entire request if email fails
    
    return {"status": "ok", "message": f"Call for package {finish_request.tracking_id} finished and transcript logged."}
