import sqlite3, datetime

# ── 1. connect (reuse your existing connection if you already have one) ──
conn = sqlite3.connect("app.db")          # adjust path if needed
cur = conn.cursor()

# ── 2. create tables if they’re not there ──
cur.executescript("""
CREATE TABLE IF NOT EXISTS packages(
  id            INTEGER PRIMARY KEY,
  tracking_id   TEXT UNIQUE,
  customer_name TEXT,
  phone         TEXT,
  address       TEXT,
  postal_code   TEXT,
  email         TEXT,
  scheduled_at  TEXT,
  status        TEXT
);
CREATE TABLE IF NOT EXISTS call_logs(
  id          INTEGER PRIMARY KEY,
  tracking_id TEXT,
  transcript  TEXT,
  completed   INTEGER,
  escalated   INTEGER,
  created_at  TEXT DEFAULT (datetime('now'))
);
""")

# ── 3. seed sample data ──
packages = [
    # tracking_id, customer_name, phone, address, postal, email,
    # scheduled_at (ISO-8601 string), status
    ("TRACK123", "John Doe",  "1234567890",
     "123 Main St, Anytown",  "12345", "justwantpost@gmail.com",
     "2025-08-03 09:00:00",   "Out for Delivery"),    # eligible

    ("TRACK456", "Jane Smith", "0987654321",
     "99 North Ave, Othertown", "98765", "justwantpost@gmail.com",
     "2025-08-04 14:00:00",    "Scheduled")           # also eligible
]
cur.executemany(
    """INSERT OR IGNORE INTO packages
       (tracking_id, customer_name, phone, address, postal_code,
        email, scheduled_at, status)
       VALUES (?,?,?,?,?,?,?,?)""",
    packages
)

call_logs = [
    # tracking_id, transcript, completed, escalated, created_at
    ("TRACK123", "Seeded test log (no action yet)", 0, 0,
     datetime.datetime.now().isoformat(timespec="seconds")),
    ("XYZINVALID", "Seeded failed verification – escalated", 0, 1,
     datetime.datetime.now().isoformat(timespec="seconds"))
]
cur.executemany(
    """INSERT INTO call_logs
       (tracking_id, transcript, completed, escalated, created_at)
       VALUES (?,?,?,?,?)""",
    call_logs
)

conn.commit()

# ── 4. sanity-check: print what we just inserted ──
print("\nPackages table:")
for row in cur.execute("SELECT * FROM packages"):
    print(row)

print("\nCall logs table:")
for row in cur.execute("SELECT * FROM call_logs"):
    print(row)
