# COMPLETE_ATTRACTIVE_CONTRACTOR_SITE_60MIN_EXPIRE_2026_10_22
# Restored professional look & feel from ~Oct 18 (Inter font, gradients, badges, benefits, clean modern design)
# + All recent features: demo seed 50/100, persistent admin for alamotte1956@gmail.com,
# demo buy process, Stripe-ready (commented), exclusive messaging, privacy/terms.

from flask import Flask, request, redirect, url_for, session, flash, jsonify
import sqlite3, os, random, smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from functools import wraps

try:
    from twilio.rest import Client
except ImportError:
    Client = None

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")
app.permanent_session_lifetime = timedelta(days=365)

DB = "leads.db"

SERVICES = [
    "Water Damage Restoration", "Mold Mitigation / Remediation", "Mold Inspection",
    "Dry Out Services", "Indoor Air Quality Testing", "Roofing", "Siding", "Windows",
    "Kitchen Remodeling", "Bathroom Remodeling", "Home Additions", "General Remodeling",
    "HVAC", "Plumbing", "Electrical", "Flooring", "Painting", "Other"
]

ZIPS = ["55305","55311","55331","55343","55344","55345","55346","55347","55356","55357",
        "55359","55364","55369","55374","55391","55392","55416","55420","55423","55424",
        "55425","55426","55431","55435","55436","55437","55438","55439"]

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
                services TEXT, license_number TEXT, insurance TEXT,
                active INTEGER DEFAULT 1, agreement_accepted INTEGER DEFAULT 0,
                agreement_at TIMESTAMP, password_hash TEXT,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, phone TEXT, email TEXT, zip TEXT,
                service_type TEXT, details TEXT, urgency TEXT,
                status TEXT DEFAULT 'available', assigned_to INTEGER,
                price REAL DEFAULT 45.0, qualification_score INTEGER DEFAULT 0,
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

def qualify_lead(urgency, details, zipc):
    """Simple Angi/Thumbtack-style qualification score (0-100)."""
    score = 50
    u = (urgency or "").lower()
    if u == "emergency": score += 30
    elif u == "high": score += 20
    elif u == "medium": score += 10
    d = (details or "").lower()
    if any(w in d for w in ["flood", "burst", "leak", "mold", "emergency", "immediate"]):
        score += 15
    if zipc in ZIPS:
        score += 5
    return min(100, score)

def send_sms(to_phone, body):
    """Send SMS via Twilio if credentials are set."""
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_num = os.environ.get("TWILIO_FROM")
    if not all([sid, token, from_num, Client]):
        print(f"[SMS skipped] {to_phone}: {body}")
        return
    try:
        client = Client(sid, token)
        client.messages.create(body=body, from_=from_num, to=to_phone)
    except Exception as e:
        print(f"[SMS error] {e}")

def send_email(to_email, subject, body):
    """Send email via SMTP if credentials are set."""
    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", 587))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    if not all([host, user, password]):
        print(f"[Email skipped] {to_email}: {subject}")
        return
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to_email
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
    except Exception as e:
        print(f"[Email error] {e}")
    s = (service or "").lower()
    if any(x in s for x in ["water", "mold", "dry out", "air quality"]):
        return 54.0
    if any(x in s for x in ["roof", "siding", "window"]):
        return 50.0
    if any(x in s for x in ["kitchen", "bath", "remodel", "addition"]):
        return 45.0
    return 40.0

ADMIN_EMAILS = ["alamotte1956@gmail.com", "admin@example.com"]
ADMIN_PASS = "demo"

def login_required(f):
    @wraps(f)
    def wrap(*a, **k):
        if "contractor_id" not in session:
            return redirect("/contractor_login")
        return f(*a, **k)
    return wrap

def admin_required(f):
    @wraps(f)
    def wrap(*a, **k):
        if not session.get("is_admin"):
            return redirect("/admin_login")
        return f(*a, **k)
    return wrap

# Professional restored stylesheet (Inter + gradients + badges + modern cards)
STYLE = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root { --blue: #0ea5e9; --blue2: #0284c7; --navy: #0f172a; --teal: #0e7490; --bg: #f8fafc; --green: #059669; }
* { box-sizing: border-box; }
body { font-family: 'Inter', system-ui, sans-serif; margin: 0; background: var(--bg); color: #0f172a; }
.header, .hero { background: linear-gradient(160deg, #0f172a 0%, #0e7490 100%); color: white; padding: 64px 24px 48px; text-align: center; }
.header h1, .hero h1 { margin: 0; font-size: 2.6rem; font-weight: 700; letter-spacing: -0.03em; }
.header p, .hero p { margin: 12px 0 0; opacity: 0.92; font-size: 1.15rem; max-width: 640px; margin-left: auto; margin-right: auto; }
.badges { display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin-top: 24px; }
.badge { background: rgba(255,255,255,0.12); backdrop-filter: blur(8px); padding: 8px 16px; border-radius: 999px; font-weight: 600; font-size: 0.9rem; }
.nav { background: white; padding: 14px 20px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.08); position: sticky; top: 0; z-index: 10; }
.nav a { display: inline-block; margin: 6px; padding: 10px 18px; background: var(--blue); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; }
.nav a:hover { background: var(--blue2); }
.container { max-width: 1000px; margin: 40px auto; padding: 0 20px; }
.card { background: white; border-radius: 16px; padding: 32px; box-shadow: 0 4px 24px rgba(0,0,0,0.06); margin-bottom: 24px; }
.note { background: #f0fdf4; color: #166534; padding: 16px 18px; border-radius: 12px; font-weight: 600; border-left: 4px solid #10b981; margin-bottom: 20px; }
.red-note { background: #fef2f2; color: #991b1b; padding: 14px 16px; border-radius: 10px; font-weight: 600; border-left: 4px solid #ef4444; }
input, textarea, select, button { width: 100%; padding: 14px; margin: 8px 0; border: 1px solid #e2e8f0; border-radius: 10px; box-sizing: border-box; font-size: 15px; font-family: inherit; }
button { background: var(--blue); color: white; border: none; font-weight: 600; cursor: pointer; font-size: 1rem; }
button:hover { background: var(--blue2); }
button.green { background: var(--green); }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 12px; border-bottom: 1px solid #e2e8f0; }
select[multiple] { height: 160px; }
.legal { font-size: 15px; line-height: 1.65; }
.benefits { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-top: 24px; }
.benefit { background: #f8fafc; padding: 20px; border-radius: 12px; }
.benefit h3 { margin: 0 0 8px; font-size: 1.05rem; }
"""

@app.route("/")
def home():
    return f"""<!DOCTYPE html>
<html lang="en"><head><title>Best Leads — Exclusive Twin Cities</title>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="hero">
  <h1>Exclusive Leads.<br>Higher Close Rates.</h1>
  <p>One contractor per job. No shared leads. Twin Cities only. ~10–20% below typical Angi rates. No monthly fee.</p>
  <div class="badges">
    <span class="badge">No Shared Leads</span>
    <span class="badge">~10–20% Below Angi</span>
    <span class="badge">No Monthly Fee</span>
    <span class="badge">Quality Gated</span>
  </div>
</div>
<div class="nav">
  <a href="/signup">Contractor Signup</a>
  <a href="/available_leads">Available Leads</a>
  <a href="/my_assignments">My Assignments</a>
  <a href="/contractor_login">Login</a>
  <a href="/admin">Admin</a>
  <a href="/seed_demo">Seed Demo Data</a>
  <a href="/privacy">Privacy</a>
  <a href="/terms">Terms</a>
</div>
<div class="container">
  <div class="note">No shared leads. Your phone will not ring with competing contractors.</div>
  <div class="card">
    <h2>Why Contractors Choose Best Leads</h2>
    <div class="benefits">
      <div class="benefit"><h3>Exclusive Only</h3><p>One contractor per lead. No competition on the job.</p></div>
      <div class="benefit"><h3>Higher Close Rates</h3><p>Homeowners expect one contractor. You convert more.</p></div>
      <div class="benefit"><h3>Lower Cost</h3><p>Prices set ~10–20% below typical shared lead platforms.</p></div>
      <div class="benefit"><h3>Quality Focus</h3><p>Twin Cities zips only. Leads expire after 60 minutes if not accepted.</p></div>
    </div>
  </div>
</div>
</body></html>"""

@app.route("/seed_demo")
def seed_demo():
    with get_db() as db:
        db.execute("DELETE FROM assignments")
        db.execute("DELETE FROM leads")
        db.execute("DELETE FROM contractors WHERE email LIKE '%demo%' OR email LIKE '%example.com'")

        first = ["Alex","Jordan","Taylor","Casey","Morgan","Riley","Avery","Quinn","Blake","Cameron","Drew","Emerson","Finley","Harper","Jamie","Kendall","Logan","Parker","Reese","Skyler"]
        last = ["Anderson","Berg","Carlson","Dahl","Erickson","Fischer","Gustafson","Hanson","Iverson","Johansen","Larson","Nelson","Olson","Peterson","Swanson","Thompson","Williams","Johnson","Miller","Davis"]
        companies = ["Twin Cities Restoration","Metro Mold Pros","West Suburbs Roofing","Edina Remodel Co","Minnetonka Builders","Excelsior Services","Bloomington Restoration","Eden Prairie Contractors","Wayzata Pros","St Louis Park Home"]

        for i in range(50):
            name = f"{random.choice(first)} {random.choice(last)} {i+1}"
            email = f"demo{i+1}@example.com"
            phone = f"(612) 555-{1000+i:04d}"
            company = random.choice(companies)
            svcs = ", ".join(random.sample(SERVICES, k=random.randint(1, 4)))
            db.execute("""INSERT INTO contractors (name, email, phone, company, services, active, agreement_accepted)
                          VALUES (?, ?, ?, ?, ?, 1, 1)""", (name, email, phone, company, svcs))

        urgencies = ["Emergency", "High", "Medium", "Low"]
        details = ["Basement flooded after heavy rain", "Visible mold in bathroom", "Roof leak after storm", "Kitchen remodel needed", "Water damage from burst pipe", "Attic mold inspection", "Siding replacement", "Window replacement project"]
        for i in range(100):
            svc = random.choice(SERVICES)
            price = get_price(svc)
            name = f"Homeowner {i+1}"
            phone = f"(952) 555-{2000+i:04d}"
            email = f"lead{i+1}@example.com"
            zipc = random.choice(ZIPS)
            urgency = random.choice(urgencies)
            detail = random.choice(details)
            created = datetime.utcnow() - timedelta(minutes=random.randint(0, 90))
            expires = created + timedelta(minutes=60)
            score = qualify_lead(urgency, detail, zipc)
            db.execute("""INSERT INTO leads (name, phone, email, zip, service_type, details, urgency, price, qualification_score, created, expires_at, status)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'available')""",
                       (name, phone, email, zipc, svc, detail, urgency, price, score, created, expires))

    flash("Demo data seeded: 50 contractors and 100 exclusive leads.")
    return redirect("/admin")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        company = request.form.get("company", "")
        services_list = request.form.getlist("services")
        services = ", ".join(services_list) if services_list else ""
        with get_db() as db:
            try:
                db.execute("""INSERT INTO contractors (name, email, phone, company, services, agreement_accepted, agreement_at)
                              VALUES (?, ?, ?, ?, ?, 1, ?)""",
                           (name, email, phone, company, services, datetime.utcnow()))
                flash("Account created. Please log in.")
                return redirect("/contractor_login")
            except sqlite3.IntegrityError:
                flash("Email already registered.")
                return redirect("/signup")
    options = "".join([f'<option value="{s}">{s}</option>' for s in SERVICES])
    return f"""<!DOCTYPE html>
<html lang="en"><head><title>Contractor Signup</title>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header"><h1>Contractor Signup</h1><p>Exclusive Twin Cities leads. No shared jobs.</p></div>
<div class="nav"><a href="/">Home</a></div>
<div class="container">
  <div class="card">
    <form method="post">
      <input name="name" placeholder="Full name" required>
      <input name="email" type="email" placeholder="Email" required>
      <input name="password" type="password" placeholder="Password" required>
      <input name="phone" placeholder="Phone" required>
      <input name="company" placeholder="Company">
      <label style="display:block; margin-top:12px; font-weight:600;">Services Offered (hold Ctrl/Cmd to select multiple)</label>
      <select name="services" multiple required>{options}</select>
      <button>Create Account</button>
    </form>
  </div>
</div>
</body></html>"""

@app.route("/contractor_login", methods=["GET", "POST"])
def contractor_login():
    if request.method == "POST":
        email = request.form.get("email")
        with get_db() as db:
            c = db.execute("SELECT * FROM contractors WHERE email=?", (email,)).fetchone()
            if c:
                session["contractor_id"] = c["id"]
                session["contractor_name"] = c["name"]
                return redirect("/available_leads")
        flash("Invalid login")
    return f"""<!DOCTYPE html>
<html lang="en"><head><title>Login</title>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header"><h1>Contractor Login</h1></div>
<div class="nav"><a href="/">Home</a></div>
<div class="container">
  <div class="card">
    <form method="post">
      <input name="email" type="email" placeholder="Email" required>
      <input name="password" type="password" placeholder="Password" required>
      <button>Login</button>
    </form>
    <p style="margin-top:16px; color:#64748b;">Demo logins: demo1@example.com through demo50@example.com (any password)</p>
  </div>
</div>
</body></html>"""

@app.route("/available_leads")
@login_required
def available_leads():
    now = datetime.utcnow()
    with get_db() as db:
        # Only unassigned, non-expired leads
        leads = db.execute("""
            SELECT * FROM leads 
            WHERE status='available' AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY qualification_score DESC, created DESC LIMIT 50
        """, (now,)).fetchall()
    rows = ""
    for lead in leads:
        rows += f"""<tr>
            <td>{lead['service_type']}</td>
            <td>{lead['zip']}</td>
            <td>{lead['urgency']}</td>
            <td>Score: {lead['qualification_score']}</td>
            <td>${lead['price']:.0f}</td>
            <td><form method="post" action="/claim/{lead['id']}"><button class="green">Claim Lead</button></form></td>
        </tr>"""
    if not rows:
        rows = "<tr><td colspan='6'>No available leads right now. Seed demo data if needed.</td></tr>"
    return f"""<!DOCTYPE html>
<html lang="en"><head><title>Available Leads</title>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header"><h1>Available Exclusive Leads</h1><p>One contractor per job. Contact info hidden until accepted.</p></div>
<div class="nav"><a href="/">Home</a> <a href="/my_assignments">My Assignments</a> <a href="/logout">Logout</a></div>
<div class="container">
  <div class="note">No shared leads. Contact information is revealed only after you accept the assignment.</div>
  <div class="red-note">You have 60 minutes to accept or reject once claimed. You are not charged until you accept.</div>
  <div class="card">
    <p>Welcome {session.get('contractor_name', 'Contractor')}</p>
    <table>
      <tr><th>Service</th><th>Zip</th><th>Urgency</th><th>Quality</th><th>Price</th><th>Action</th></tr>
      {rows}
    </table>
  </div>
</div>
</body></html>"""

@app.route("/claim/<int:lead_id>", methods=["POST"])
@login_required
def claim(lead_id):
    cid = session["contractor_id"]
    now = datetime.utcnow()
    expires = now + timedelta(minutes=60)
    with get_db() as db:
        lead = db.execute("SELECT * FROM leads WHERE id=? AND status='available' AND (expires_at IS NULL OR expires_at > ?)", (lead_id, now)).fetchone()
        if not lead:
            flash("Lead no longer available.")
            return redirect("/available_leads")
        # Mark as pending assignment (not charged yet)
        db.execute("UPDATE leads SET status='pending', assigned_to=? WHERE id=?", (cid, lead_id))
        db.execute("INSERT INTO assignments (lead_id, contractor_id, status, expires_at) VALUES (?, ?, 'pending', ?)", (lead_id, cid, expires))
        # SMS alert to contractor
        c = db.execute("SELECT phone FROM contractors WHERE id=?", (cid,)).fetchone()
        if c and c["phone"]:
            send_sms(c["phone"], f"New exclusive lead claimed: {lead['service_type']} in {lead['zip']}. You have 60 minutes to accept or reject. No charge until you accept.")
        flash("Lead claimed. You have 60 minutes to accept or reject. You are not charged until you accept.")
    return redirect("/my_assignments")

@app.route("/my_assignments")
@login_required
def my_assignments():
    cid = session["contractor_id"]
    now = datetime.utcnow()
    with get_db() as db:
        assigns = db.execute("""
            SELECT a.*, l.service_type, l.zip, l.urgency, l.price, l.qualification_score, l.details,
                   l.name, l.phone, l.email
            FROM assignments a
            JOIN leads l ON l.id = a.lead_id
            WHERE a.contractor_id=? AND a.status='pending' AND a.expires_at > ?
            ORDER BY a.created DESC
        """, (cid, now)).fetchall()
    rows = ""
    for a in assigns:
        # Hide contact info until accepted
        rows += f"""<tr>
            <td>{a['service_type']}</td>
            <td>{a['zip']}</td>
            <td>{a['urgency']}</td>
            <td>Score: {a['qualification_score']}</td>
            <td>${a['price']:.0f}</td>
            <td>
              <form method="post" action="/accept/{a['id']}" style="display:inline"><button class="green">Accept</button></form>
              <form method="post" action="/reject/{a['id']}" style="display:inline"><button style="background:#dc2626">Reject</button></form>
            </td>
        </tr>"""
    if not rows:
        rows = "<tr><td colspan='6'>No pending assignments. Claim a lead first.</td></tr>"
    return f"""<!DOCTYPE html>
<html lang="en"><head><title>My Assignments</title>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header"><h1>My Pending Assignments</h1><p>Accept within 60 minutes or the lead is released. No charge until you accept.</p></div>
<div class="nav"><a href="/available_leads">Available Leads</a> <a href="/logout">Logout</a></div>
<div class="container">
  <div class="red-note">Contact information is revealed only after you accept. You are not charged until acceptance.</div>
  <div class="card">
    <table>
      <tr><th>Service</th><th>Zip</th><th>Urgency</th><th>Quality</th><th>Price</th><th>Action</th></tr>
      {rows}
    </table>
  </div>
</div>
</body></html>"""

@app.route("/accept/<int:assignment_id>", methods=["POST"])
@login_required
def accept(assignment_id):
    cid = session["contractor_id"]
    now = datetime.utcnow()
    with get_db() as db:
        a = db.execute("SELECT * FROM assignments WHERE id=? AND contractor_id=? AND status='pending' AND expires_at > ?", (assignment_id, cid, now)).fetchone()
        if not a:
            flash("Assignment expired or invalid.")
            return redirect("/my_assignments")
        # Accept: mark lead sold, reveal contact later, charge would happen here in real Stripe
        db.execute("UPDATE assignments SET status='accepted' WHERE id=?", (assignment_id,))
        db.execute("UPDATE leads SET status='sold', assigned_to=? WHERE id=?", (cid, a["lead_id"]))
        # Email the customer that a contractor will call
        lead = db.execute("SELECT * FROM leads WHERE id=?", (a["lead_id"],)).fetchone()
        contractor = db.execute("SELECT * FROM contractors WHERE id=?", (cid,)).fetchone()
        if lead and lead["email"] and contractor:
            body = f"""Hello {lead['name']},

A contractor has accepted your exclusive lead for {lead['service_type']}.

{contractor['name']} ({contractor.get('company') or 'Independent Contractor'}) will be contacting you shortly with a quote.

Phone: {contractor.get('phone') or 'On file'}

Thank you for using Best Leads.
"""
            send_email(lead["email"], "Your contractor will contact you with a quote", body)
        flash("Lead accepted. Contact information is now available. Customer has been notified by email. (Demo: no charge applied.)")
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
            flash("Lead rejected and released back to the available pool.")
    return redirect("/my_assignments")

@app.route("/my_leads")
@login_required
def my_leads():
    cid = session["contractor_id"]
    with get_db() as db:
        leads = db.execute("""
            SELECT l.* FROM leads l
            JOIN assignments a ON a.lead_id = l.id
            WHERE a.contractor_id=? AND a.status='accepted'
            ORDER BY a.created DESC
        """, (cid,)).fetchall()
    rows = ""
    for lead in leads:
        rows += f"""<tr>
            <td>{lead['service_type']}</td>
            <td>{lead['name']}</td>
            <td>{lead['phone']}</td>
            <td>{lead['email']}</td>
            <td>{lead['zip']}</td>
            <td>{lead['details']}</td>
        </tr>"""
    if not rows:
        rows = "<tr><td colspan='6'>No accepted leads yet.</td></tr>"
    return f"""<!DOCTYPE html>
<html lang="en"><head><title>My Accepted Leads</title>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header"><h1>My Accepted Leads</h1><p>Contact information is shown only for leads you have accepted.</p></div>
<div class="nav"><a href="/available_leads">Available Leads</a> <a href="/my_assignments">Pending</a> <a href="/logout">Logout</a></div>
<div class="container">
  <div class="card">
    <table>
      <tr><th>Service</th><th>Name</th><th>Phone</th><th>Email</th><th>Zip</th><th>Details</th></tr>
      {rows}
    </table>
  </div>
</div>
</body></html>"""

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/admin")
@admin_required
def admin():
    with get_db() as db:
        contractors = db.execute("SELECT COUNT(*) as c FROM contractors").fetchone()["c"]
        leads = db.execute("SELECT COUNT(*) as c FROM leads").fetchone()["c"]
        available = db.execute("SELECT COUNT(*) as c FROM leads WHERE status='available'").fetchone()["c"]
    return f"""<!DOCTYPE html>
<html lang="en"><head><title>Admin</title>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header"><h1>Admin Dashboard</h1></div>
<div class="nav"><a href="/">Home</a> <a href="/seed_demo">Reseed Demo Data</a></div>
<div class="container">
  <div class="card">
    <p><strong>Contractors:</strong> {contractors}</p>
    <p><strong>Total Leads:</strong> {leads}</p>
    <p><strong>Available Leads:</strong> {available}</p>
    <p style="margin-top:20px;"><a href="/seed_demo">Reseed 50 contractors + 100 leads</a></p>
  </div>
</div>
</body></html>"""

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("email") in ADMIN_EMAILS and request.form.get("password") == ADMIN_PASS:
            session.permanent = True
            session["is_admin"] = True
            return redirect("/admin")
        flash("Invalid admin credentials")
    return f"""<!DOCTYPE html>
<html lang="en"><head><title>Admin Login</title>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header"><h1>Admin Login</h1></div>
<div class="nav"><a href="/">Home</a></div>
<div class="container">
  <div class="card">
    <form method="post">
      <input name="email" type="email" placeholder="Email" required>
      <input name="password" type="password" placeholder="Password" required>
      <button>Login</button>
    </form>
    <p style="margin-top:16px; color:#64748b;">Use alamotte1956@gmail.com / demo (or admin@example.com / demo)</p>
  </div>
</div>
</body></html>"""

@app.route("/privacy")
def privacy():
    return f"""<!DOCTYPE html>
<html lang="en"><head><title>Privacy</title>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header"><h1>Privacy Policy</h1></div>
<div class="container"><div class="card legal">
<p>Last Updated: October 22, 2026</p>
<p>We collect contractor and lead information solely to operate the exclusive lead matching service. We do not share leads with multiple contractors.</p>
<p><a href="/">Back</a></p>
</div></div>
</body></html>"""

@app.route("/terms")
def terms():
    return f"""<!DOCTYPE html>
<html lang="en"><head><title>Terms</title>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header"><h1>Terms & Conditions</h1></div>
<div class="container"><div class="card legal">
<p>Last Updated: October 22, 2026</p>
<p>Exclusive leads only. Minnesota law governs. Leads expire after 60 minutes if not accepted. Prices are competitive and approximately 10–20% below typical Angi shared lead rates. No monthly fee.</p>
<p><a href="/">Back</a></p>
</div></div>
</body></html>"""

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
