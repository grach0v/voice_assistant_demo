# import sqlite3, datetime
import json
import datetime

# ── Commented out SQL database code ──
# conn = sqlite3.connect("app.db")          # adjust path if needed
# cur = conn.cursor()

# ── 2. create tables if they're not there ──
# cur.executescript("""
# CREATE TABLE IF NOT EXISTS packages(
#   id            INTEGER PRIMARY KEY,
#   tracking_id   TEXT UNIQUE,
#   customer_name TEXT,
#   phone         TEXT,
#   address       TEXT,
#   postal_code   TEXT,
#   email         TEXT,
#   scheduled_at  TEXT,
#   status        TEXT
# );
# CREATE TABLE IF NOT EXISTS call_logs(
#   id          INTEGER PRIMARY KEY,
#   tracking_id TEXT,
#   transcript  TEXT,
#   completed   INTEGER,
#   escalated   INTEGER,
#   created_at  TEXT DEFAULT (datetime('now'))
# );
# """)

# ── 3. Create JSON data instead ──
data = {
    "packages": [
        {
            "id": 1,
            "tracking_id": "TRACK123",
            "customer_name": "John Doe",
            "phone": "1234567890",
            "address": "123 Main St, Anytown",
            "postal_code": "12345",
            "email": "justwantpost@gmail.com",
            "scheduled_at": "2025-08-03 09:00:00",
            "status": "Out for Delivery"
        },
        {
            "id": 2,
            "tracking_id": "TRACK456",
            "customer_name": "Jane Smith",
            "phone": "0987654321",
            "address": "99 North Ave, Othertown",
            "postal_code": "98765",
            "email": "justwantpost@gmail.com",
            "scheduled_at": "2025-08-04 14:00:00",
            "status": "Scheduled"
        }
    ],
    "call_logs": [
        {
            "id": 1,
            "tracking_id": "TRACK123",
            "transcript": "Seeded test log (no action yet)",
            "completed": 0,
            "escalated": 0,
            "created_at": datetime.datetime.now().isoformat(timespec="seconds")
        },
        {
            "id": 2,
            "tracking_id": "XYZINVALID",
            "transcript": "Seeded failed verification – escalated",
            "completed": 0,
            "escalated": 1,
            "created_at": datetime.datetime.now().isoformat(timespec="seconds")
        }
    ]
}

# Write to JSON file
with open("data.json", "w") as f:
    json.dump(data, f, indent=2)

print("JSON data file created: data.json")
print("\nPackages:")
for pkg in data["packages"]:
    print(pkg)

print("\nCall logs:")
for log in data["call_logs"]:
    print(log)
