# Contractor sales site - reconstructed from ~Oct 16-19 working version
# Blue header, exclusive leads, claim/accept flow, 60-min window, no contact info until accept
from flask import Flask, request, redirect, session, flash
import sqlite3, os, random
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "demo-secret-key")

DB = "leads.db"

def get_db():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS contractors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, email TEXT UNIQUE, phone TEXT, company TEXT,
                services TEXT, active INTEGER DEFAULT 1,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, phone TEXT, email TEXT, zip TEXT,
                service_type TEXT, details TEXT, urgency TEXT,
                status TEXT DEFAULT 'available', assigned_to INTEGER,
                price REAL DEFAULT 45.0, qualification_score INTEGER DEFAULT 70,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER, contractor_id INTEGER,
                status TEXT DEFAULT 'pending',
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            );
        """)

init_db()

SERVICES = ["Water Damage Restoration", "Mold Remediation", "Dry Out Services", "Roofing", "Siding", "Windows", "Kitchen Remodel", "Bathroom Remodel"]
ZIPS = ["55416", "55343", "55344", "55345", "55346", "55347", "55391", "55369", "55435", "55436", "55437", "55438", "55439", "55420", "55425", "55431"]

def get_price(service):
    s = (service or "").lower()
    if any(x in s for x in ["water", "mold", "dry"]):
        return 54.0
    if any(x in s for x in ["roof", "siding", "window"]):
        return 50.0
    return 45.0

STYLE = """
body { font-family: Segoe UI, sans-serif; margin:0; background:#f1f5f9; color:#0f172a; }
.header { background: linear-gradient(135deg, #0c4a6e, #0369a1); color:white; padding:28px 20px; text-align:center; }
.nav { background:white; padding:12px; text-align:center; box-shadow:0 2px 8px rgba(0,0,0,0.06); }
.nav a { display:inline-block; margin:6px; padding:10px 16px; background:#0369a1; color:white; text-decoration:none; border-radius:8px; font-weight:600; }
.container { max-width:1000px; margin:30px auto; padding:0 20px; }
.card { background:white; border-radius:12px; padding:24px; box-shadow:0 4px 16px rgba(0,0,0,0.05); margin-bottom:20px; }
.note { background:#f0fdf4; color:#166534; padding:14px; border-radius:8px; font-weight:600; margin-bottom:16px; }
.red-note { background:#fef2f2; color:#991b1b; padding:12px; border-radius:8px; font-weight:600; }
button { background:#0369a1; color:white; border:none; padding:12px 18px; border-radius:8px; font-weight:600; cursor:pointer; }
button.orange { background:#f97316; }
button.orange:hover { background:#ea580c; }
table { width:100%; border-collapse:collapse; }
th, td { padding:10px; border-bottom:1px solid #e2e8f0; text-align:left; }
"""

@app.route("/")
def home():
    return f"""<!DOCTYPE html>
<html><head><title>Best Leads</title><style>{STYLE}</style></head><body>
<div class="header"><h1>Best Leads</h1><p>Exclusive Twin Cities Leads — One Contractor Per Job</p></div>
<div class="nav">
  <a href="/signup">Signup</a>
  <a href="/available_leads">Available Leads</a>
  <a href="/my_assignments">My Assignments</a>
  <a href="/contractor_login">Login</a>
  <a href="/seed_demo">Seed Demo</a>
</div>
<div class="container">
  <div class="note">No shared leads. Contact info hidden until you accept.</div>
  <div class="card">
    <h2>Contractor Dashboard</h2>
    <p>Claim a lead, then accept or reject within 60 minutes. You are not charged until you accept.</p>
    <p><a href="/available_leads"><button class="orange">View Available Leads</button></a></p>
  </div>
</div></body></html>"""

@app.route("/seed_demo")
def seed_demo():
    with get_db() as db:
        db.execute("DELETE FROM assignments")
        db.execute("DELETE FROM leads")
        db.execute("DELETE FROM contractors WHERE email LIKE '%demo%' OR email LIKE '%example.com'")
        for i in range(20):
            db.execute("INSERT INTO contractors (name, email, phone, company, services, active) VALUES (?, ?, ?, ?, ?, 1)",
                       (f"Contractor {i+1}", f"demo{i+1}@example.com", f"(612) 555-{1000+i:04d}", "Local Pro", "Water Damage, Mold",))
        for i in range(40):
            svc = random.choice(SERVICES)
            created = datetime.utcnow() - timedelta(minutes=random.randint(0, 50))
            expires = created + timedelta(minutes=60)
            db.execute("""INSERT INTO leads (name, phone, email, zip, service_type, details, urgency, price, created, expires_at, status)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'available')""",
                       (f"Homeowner {i+1}", f"(952) 555-{2000+i:04d}", f"lead{i+1}@example.com",
                        random.choice(ZIPS), svc, "Detailed job description here", random.choice(["Emergency","High","Medium"]),
                        get_price(svc), created, expires))
    flash("Demo data seeded.")
    return redirect("/")

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        with get_db() as db:
            try:
                db.execute("INSERT INTO contractors (name, email, phone, company, services) VALUES (?, ?, ?, ?, ?)",
                           (request.form["name"], request.form["email"], request.form["phone"], request.form.get("company",""), "General"))
                flash("Account created. Please log in.")
                return redirect("/contractor_login")
            except:
                flash("Email already exists.")
    return f"""<!DOCTYPE html>
<html><head><title>Signup</title><style>{STYLE}</style></head><body>
<div class="header"><h1>Contractor Signup</h1></div>
<div class="container"><div class="card">
<form method="post">
  <input name="name" placeholder="Full name" required><br>
  <input name="email" type="email" placeholder="Email" required><br>
  <input name="phone" placeholder="Phone" required><br>
  <input name="company" placeholder="Company"><br>
  <button class="orange">Create Account</button>
</form></div></div></body></html>"""

@app.route("/contractor_login", methods=["GET","POST"])
def contractor_login():
    if request.method == "POST":
        with get_db() as db:
            c = db.execute("SELECT * FROM contractors WHERE email=?", (request.form["email"],)).fetchone()
            if c:
                session["contractor_id"] = c["id"]
                session["contractor_name"] = c["name"]
                return redirect("/available_leads")
        flash("Login failed.")
    return f"""<!DOCTYPE html>
<html><head><title>Login</title><style>{STYLE}</style></head><body>
<div class="header"><h1>Contractor Login</h1></div>
<div class="container"><div class="card">
<form method="post">
  <input name="email" type="email" placeholder="Email" required><br>
  <button class="orange">Login</button>
</form>
<p>Demo: demo1@example.com (any password)</p>
</div></div></body></html>"""

def login_required(f):
    @wraps(f)
    def wrap(*a, **k):
        if "contractor_id" not in session:
            return redirect("/contractor_login")
        return f(*a, **k)
    return wrap

@app.route("/available_leads")
@login_required
def available_leads():
    now = datetime.utcnow()
    with get_db() as db:
        leads = db.execute("SELECT * FROM leads WHERE status='available' AND (expires_at IS NULL OR expires_at > ?) ORDER BY created DESC LIMIT 40", (now,)).fetchall()
    rows = ""
    for lead in leads:
        rows += f"""<tr>
            <td>{lead['service_type']}</td><td>{lead['zip']}</td><td>{lead['urgency']}</td><td>${lead['price']:.0f}</td>
            <td><form method="post" action="/claim/{lead['id']}"><button class="orange">Claim Lead</button></form></td>
        </tr>"""
    if not rows: rows = "<tr><td colspan='5'>No leads available.</td></tr>"
    return f"""<!DOCTYPE html>
<html><head><title>Available Leads</title><style>{STYLE}</style></head><body>
<div class="header"><h1>Available Exclusive Leads</h1></div>
<div class="nav"><a href="/">Home</a> <a href="/my_assignments">My Assignments</a> <a href="/logout">Logout</a></div>
<div class="container">
  <div class="note">Contact info hidden until accepted. 60 minutes to accept after claiming.</div>
  <div class="card"><table>
    <tr><th>Service</th><th>Zip</th><th>Urgency</th><th>Price</th><th>Action</th></tr>
    {rows}
  </table></div>
</div></body></html>"""

@app.route("/claim/<int:lead_id>", methods=["POST"])
@login_required
def claim(lead_id):
    cid = session["contractor_id"]
    now = datetime.utcnow()
    expires = now + timedelta(minutes=60)
    with get_db() as db:
        lead = db.execute("SELECT * FROM leads WHERE id=? AND status='available'", (lead_id,)).fetchone()
        if not lead:
            flash("Lead no longer available.")
            return redirect("/available_leads")
        db.execute("UPDATE leads SET status='pending', assigned_to=? WHERE id=?", (cid, lead_id))
        db.execute("INSERT INTO assignments (lead_id, contractor_id, status, expires_at) VALUES (?, ?, 'pending', ?)", (lead_id, cid, expires))
        flash("Lead claimed. You have 60 minutes to accept or reject.")
    return redirect("/my_assignments")

@app.route("/my_assignments")
@login_required
def my_assignments():
    cid = session["contractor_id"]
    now = datetime.utcnow()
    with get_db() as db:
        assigns = db.execute("""SELECT a.*, l.service_type, l.zip, l.urgency, l.price
            FROM assignments a JOIN leads l ON l.id = a.lead_id
            WHERE a.contractor_id=? AND a.status='pending' AND a.expires_at > ?""", (cid, now)).fetchall()
    rows = ""
    for a in assigns:
        rows += f"""<tr>
            <td>{a['service_type']}</td><td>{a['zip']}</td><td>{a['urgency']}</td><td>${a['price']:.0f}</td>
            <td>
              <form method="post" action="/accept/{a['id']}" style="display:inline"><button class="orange">Accept</button></form>
              <form method="post" action="/reject/{a['id']}" style="display:inline"><button style="background:#dc2626">Reject</button></form>
            </td>
        </tr>"""
    if not rows: rows = "<tr><td colspan='5'>No pending assignments.</td></tr>"
    return f"""<!DOCTYPE html>
<html><head><title>My Assignments</title><style>{STYLE}</style></head><body>
<div class="header"><h1>My Pending Assignments</h1></div>
<div class="container"><div class="card"><table>
<tr><th>Service</th><th>Zip</th><th>Urgency</th><th>Price</th><th>Action</th></tr>
{rows}
</table></div></div></body></html>"""

@app.route("/accept/<int:assignment_id>", methods=["POST"])
@login_required
def accept(assignment_id):
    cid = session["contractor_id"]
    with get_db() as db:
        a = db.execute("SELECT * FROM assignments WHERE id=? AND contractor_id=? AND status='pending'", (assignment_id, cid)).fetchone()
        if a:
            db.execute("UPDATE assignments SET status='accepted' WHERE id=?", (assignment_id,))
            db.execute("UPDATE leads SET status='sold' WHERE id=?", (a["lead_id"],))
            flash("Lead accepted. Contact info now available in My Leads.")
    return redirect("/my_leads")

@app.route("/reject/<int:assignment_id>", methods=["POST"])
@login_required
def reject(assignment_id):
    cid = session["contractor_id"]
    with get_db() as db:
        a = db.execute("SELECT * FROM assignments WHERE id=? AND contractor_id=? AND status='pending'", (assignment_id, cid)).fetchone()
        if a:
            db.execute("UPDATE assignments SET status='rejected' WHERE id=?", (assignment_id,))
            db.execute("UPDATE leads SET status='available', assigned_to=NULL WHERE id=?", (a["lead_id"],))
            flash("Lead rejected and released.")
    return redirect("/my_assignments")

@app.route("/my_leads")
@login_required
def my_leads():
    cid = session["contractor_id"]
    with get_db() as db:
        leads = db.execute("""SELECT l.* FROM leads l JOIN assignments a ON a.lead_id = l.id
            WHERE a.contractor_id=? AND a.status='accepted'""", (cid,)).fetchall()
    rows = ""
    for lead in leads:
        rows += f"""<tr><td>{lead['service_type']}</td><td>{lead['name']}</td><td>{lead['phone']}</td><td>{lead['email']}</td><td>{lead['zip']}</td><td>{lead['details']}</td></tr>"""
    if not rows: rows = "<tr><td colspan='6'>No accepted leads yet.</td></tr>"
    return f"""<!DOCTYPE html>
<html><head><title>My Leads</title><style>{STYLE}</style></head><body>
<div class="header"><h1>My Accepted Leads</h1></div>
<div class="container"><div class="card"><table>
<tr><th>Service</th><th>Name</th><th>Phone</th><th>Email</th><th>Zip</th><th>Details</th></tr>
{rows}
</table></div></div></body></html>"""

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
