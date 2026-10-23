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
:root { --blue: #0369a1; --blue2: #0284c7; --orange: #f97316; --orange2: #ea580c; --bg: #f1f5f9; --green: #059669; }
body { font-family: 'Segoe UI', system-ui, sans-serif; margin: 0; background: var(--bg); color: #0f172a; }
.header { background: linear-gradient(135deg, #0c4a6e, #0369a1); color: white; padding: 28px 20px; text-align: center; }
.header h1 { margin: 0; font-size: 2.1rem; letter-spacing: -0.5px; }
.nav { background: white; padding: 12px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.nav a { display: inline-block; margin: 6px; padding: 10px 16px; background: var(--blue); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; }
.nav a:hover { background: var(--blue2); }
button { background: var(--blue); color: white; border: none; font-weight: 600; cursor: pointer; }
button:hover { background: var(--blue2); }
button.orange { background: var(--orange); }
button.orange:hover { background: var(--orange2); }
button.green { background: var(--green); }
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
<div class="header">
  <h1>Best Leads</h1>
  <p>Exclusive Twin Cities Leads — One Contractor Per Job</p>
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
  <a href="/contractor_agreement">Contractor Agreement</a>
</div>
<div class="container">
  <div class="note">No shared leads. Your phone will not ring with competing contractors.</div>
  <div class="card">
    <h2>Contractor Dashboard</h2>
    <p>High-quality exclusive leads for Twin Cities contractors. Claim a lead, then accept or reject within 60 minutes. Contact info is revealed only after acceptance. You are not charged until you accept.</p>
    <p><a href="/available_leads"><button class="orange">View Available Leads</button></a></p>
  </div>
</div>
</body></html>"""

@app.route("/seed_demo")
def seed_demo():
    with get_db() as db:
        db.execute("DELETE FROM assignments")
        db.execute("DELETE FROM leads")
        db.execute("DELETE FROM contractors WHERE email LIKE '%demo%' OR email LIKE '%example.com'")

        # Richer contractor data (realistic Twin Cities style)
        contractors_data = [
            ("Mike Johnson", "mike.j@example.com", "(612) 555-0142", "Twin Cities Restoration Pros", "Water Damage Restoration, Mold Remediation, Dry Out Services", "MN-LIC-4421", "State Farm"),
            ("Sarah Chen", "sarah.c@example.com", "(952) 555-0187", "West Metro Mold Specialists", "Mold Inspection, Mold Remediation, Indoor Air Quality Testing", "MN-LIC-8892", "Travelers"),
            ("David Olson", "david.o@example.com", "(763) 555-0231", "Edina Roofing & Exteriors", "Roofing, Siding, Windows", "MN-LIC-1156", "Auto-Owners"),
            ("Lisa Berg", "lisa.b@example.com", "(612) 555-0345", "Minnetonka Home Builders", "Kitchen Remodeling, Bathroom Remodeling, Home Additions", "MN-LIC-6674", "Liberty Mutual"),
            ("James Peterson", "james.p@example.com", "(952) 555-0412", "Excelsior Restoration", "Water Damage Restoration, Dry Out Services, Mold Mitigation", "MN-LIC-2290", "Nationwide"),
            ("Emily Anderson", "emily.a@example.com", "(612) 555-0523", "Bloomington Remodel Co", "Kitchen Remodeling, Bathroom Remodeling, Flooring", "MN-LIC-3341", "State Farm"),
            ("Robert Larson", "robert.l@example.com", "(763) 555-0634", "Wayzata Windows & Siding", "Windows, Siding, Roofing", "MN-LIC-7785", "Travelers"),
            ("Jennifer Nelson", "jen.n@example.com", "(952) 555-0745", "St Louis Park HVAC Pros", "HVAC, Plumbing, Indoor Air Quality Testing", "MN-LIC-9921", "Auto-Owners"),
            ("Chris Swanson", "chris.s@example.com", "(612) 555-0856", "Eden Prairie Electrical", "Electrical, General Remodeling", "MN-LIC-4456", "Liberty Mutual"),
            ("Amanda Fischer", "amanda.f@example.com", "(763) 555-0967", "Plymouth Plumbing & Restoration", "Plumbing, Water Damage Restoration, Dry Out Services", "MN-LIC-5512", "Nationwide"),
        ]
        # Expand to ~50 with variations
        first = ["Alex","Jordan","Taylor","Casey","Morgan","Riley","Avery","Quinn","Blake","Cameron","Drew","Emerson","Finley","Harper","Jamie","Kendall","Logan","Parker","Reese","Skyler","Ryan","Megan","Kevin","Nicole","Brian"]
        last = ["Anderson","Berg","Carlson","Dahl","Erickson","Fischer","Gustafson","Hanson","Iverson","Johansen","Larson","Nelson","Olson","Peterson","Swanson","Thompson","Williams","Johnson","Miller","Davis","Martinez","Garcia","Rodriguez","Lee","Kim"]
        companies_extra = ["Metro Restoration", "Northstar Remodel", "Lakeside Contractors", "Summit Home Services", "Prairie Exteriors", "River Valley Builders", "Oak Grove Pros", "Maplewood Restoration", "Golden Valley HVAC", "Richfield Windows"]

        for i, base in enumerate(contractors_data):
            name, email, phone, company, svcs, lic, ins = base
            db.execute("""INSERT INTO contractors (name, email, phone, company, services, license_number, insurance, active, agreement_accepted)
                          VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1)""", (name, email, phone, company, svcs, lic, ins))

        for i in range(40):
            name = f"{random.choice(first)} {random.choice(last)}"
            email = f"demo{i+11}@example.com"
            phone = f"(612) 555-{2000+i:04d}"
            company = random.choice(companies_extra)
            svcs = ", ".join(random.sample(SERVICES, k=random.randint(2, 5)))
            lic = f"MN-LIC-{1000+i:04d}"
            ins = random.choice(["State Farm", "Travelers", "Auto-Owners", "Liberty Mutual", "Nationwide"])
            db.execute("""INSERT INTO contractors (name, email, phone, company, services, license_number, insurance, active, agreement_accepted)
                          VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1)""", (name, email, phone, company, svcs, lic, ins))

        # Richer lead data
        urgencies = ["Emergency", "High", "Medium", "Low"]
        lead_details = [
            "Basement flooded after heavy rain — 2 inches of water, need immediate dry-out and mold check.",
            "Visible black mold in bathroom ceiling and walls. Want inspection and full remediation.",
            "Roof leak after storm — water coming into attic and master bedroom. Need temporary tarp and full repair.",
            "Kitchen remodel: replace cabinets, countertops, and flooring. Looking for full-service contractor.",
            "Burst pipe under kitchen sink — water damage to cabinets and flooring. Need dry-out ASAP.",
            "Attic mold discovered during insulation inspection. Want air quality testing and remediation plan.",
            "Siding replacement on entire house — vinyl preferred, some rot around windows.",
            "Window replacement project — 12 windows, double-pane, energy-efficient.",
            "Bathroom remodel: gut and rebuild master bath, including tile, vanity, and fixtures.",
            "Water damage from upstairs bathroom leak — ceiling damage in living room below.",
            "Mold inspection requested after musty smell in basement for 3 weeks.",
            "Home addition: 400 sq ft family room off the back. Need design and build.",
            "HVAC replacement — old furnace failing, want high-efficiency system.",
            "Plumbing repair: multiple slow drains and one leaking toilet.",
            "Electrical panel upgrade needed before selling the house.",
            "Flooring: replace carpet in 3 bedrooms with hardwood or LVP.",
            "Painting interior — entire main floor and basement.",
            "Deck rebuild after rot discovered — about 200 sq ft.",
            "Gutter replacement and downspout extensions to protect foundation.",
            "Insulation and air sealing in attic to reduce energy bills.",
        ]
        first_names = ["John","Mary","Robert","Patricia","Michael","Jennifer","William","Linda","David","Elizabeth","Richard","Susan","Joseph","Jessica","Thomas","Sarah","Charles","Karen","Christopher","Nancy","Daniel","Lisa","Matthew","Betty","Anthony","Margaret"]
        last_names = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez","Martinez","Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas","Taylor","Moore","Jackson","Martin"]

        for i in range(100):
            svc = random.choice(SERVICES)
            price = get_price(svc)
            fname = random.choice(first_names)
            lname = random.choice(last_names)
            name = f"{fname} {lname}"
            phone = f"(952) 555-{3000+i:04d}"
            email = f"{fname.lower()}.{lname.lower()}{i}@example.com"
            zipc = random.choice(ZIPS)
            urgency = random.choice(urgencies)
            detail = random.choice(lead_details)
            created = datetime.utcnow() - timedelta(minutes=random.randint(0, 90))
            expires = created + timedelta(minutes=60)
            score = qualify_lead(urgency, detail, zipc)
            db.execute("""INSERT INTO leads (name, phone, email, zip, service_type, details, urgency, price, qualification_score, created, expires_at, status)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'available')""",
                       (name, phone, email, zipc, svc, detail, urgency, price, score, created, expires))

    flash("Demo data seeded: 50 contractors and 100 exclusive leads with richer details.")
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
<div class="header" style="background: linear-gradient(160deg, rgba(15,23,42,0.85), rgba(14,116,144,0.75)), url('https://images.unsplash.com/photo-1504307651254-35680f356dfd?auto=format&fit=crop&w=1600&q=80') center/cover;">
  <h1>Contractor Signup</h1><p>Exclusive Twin Cities leads. No shared jobs.</p>
</div>
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
      <label style="display:block; margin:16px 0; font-size:14px;">
        <input type="checkbox" name="agree" required style="width:auto; margin-right:8px;">
        I agree to the <a href="/contractor_agreement" target="_blank">Contractor Agreement</a>, including exclusive lead terms, 60-minute acceptance window, and Minnesota law.
      </label>
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
            <td title="{lead['details'][:80]}...">{lead['details'][:40]}...</td>
            <td><form method="post" action="/claim/{lead['id']}"><button class="orange">Claim Lead</button></form></td>
        </tr>"""
    if not rows:
        rows = "<tr><td colspan='6'>No available leads right now. Seed demo data if needed.</td></tr>"
    return f"""<!DOCTYPE html>
<html lang="en"><head><title>Available Leads</title>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header">
  <h1>Available Exclusive Leads</h1><p>One contractor per job. Contact info hidden until accepted.</p>
</div>
<div class="nav"><a href="/">Home</a> <a href="/my_assignments">My Assignments</a> <a href="/logout">Logout</a></div>
<div class="container">
  <div class="note">No shared leads. Contact information is revealed only after you accept the assignment.</div>
  <div class="red-note">You have 60 minutes to accept or reject once claimed. You are not charged until you accept.</div>
  <div class="card">
    <p>Welcome {session.get('contractor_name', 'Contractor')}</p>
    <table>
      <tr><th>Service</th><th>Zip</th><th>Urgency</th><th>Quality</th><th>Price</th><th>Details</th><th>Action</th></tr>
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
              <form method="post" action="/accept/{a['id']}" style="display:inline"><button class="orange">Accept</button></form>
              <form method="post" action="/reject/{a['id']}" style="display:inline"><button style="background:#dc2626">Reject</button></form>
            </td>
        </tr>"""
    if not rows:
        rows = "<tr><td colspan='6'>No pending assignments. Claim a lead first.</td></tr>"
    return f"""<!DOCTYPE html>
<html lang="en"><head><title>My Assignments</title>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header" style="background: linear-gradient(160deg, rgba(15,23,42,0.85), rgba(14,116,144,0.75)), url('https://images.unsplash.com/photo-1556911220-bff31c812dba?auto=format&fit=crop&w=1600&q=80') center/cover;">
  <h1>My Pending Assignments</h1><p>Accept within 60 minutes or the lead is released. No charge until you accept.</p>
</div>
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
<div class="header" style="background: linear-gradient(160deg, rgba(15,23,42,0.85), rgba(14,116,144,0.75)), url('https://images.unsplash.com/photo-1621905251189-08b45d6a269e?auto=format&fit=crop&w=1600&q=80') center/cover;">
  <h1>My Accepted Leads</h1><p>Contact information is shown only for leads you have accepted.</p>
</div>
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
<html lang="en"><head><title>Privacy Policy</title>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header"><h1>Privacy Policy</h1></div>
<div class="container"><div class="card legal">
<p><strong>Last Updated:</strong> October 22, 2026</p>
<p>Best Leads (Albert R LaMotte dba Restoration Contractors MN) collects contractor and homeowner information solely to operate an exclusive lead matching service for the Twin Cities area.</p>
<p>We do not sell or share leads with multiple contractors. Contact information is revealed only after a contractor accepts an assignment.</p>
<p>We may use SMS and email to notify contractors of claimed leads and to notify homeowners when a contractor has accepted their request.</p>
<p>This policy is governed by Minnesota law. Questions: contact the administrator.</p>
<p><a href="/">Back to Home</a> | <a href="/terms">Terms</a> | <a href="/contractor_agreement">Contractor Agreement</a></p>
</div></div>
</body></html>"""

@app.route("/terms")
def terms():
    return f"""<!DOCTYPE html>
<html lang="en"><head><title>Terms & Conditions</title>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header"><h1>Terms & Conditions</h1></div>
<div class="container"><div class="card legal">
<p><strong>Last Updated:</strong> October 22, 2026</p>
<p>These terms govern use of the Best Leads platform operated by Albert R LaMotte dba Restoration Contractors MN.</p>
<ul>
<li>Leads are exclusive — one contractor per lead.</li>
<li>Contractors have 60 minutes to accept or reject a claimed lead.</li>
<li>Contractors are not charged until they accept an assignment.</li>
<li>Contact information is provided only after acceptance.</li>
<li>Leads that are not accepted within 60 minutes return to the available pool or expire.</li>
<li>Minnesota law governs all agreements and disputes.</li>
<li>No shared leads. Your phone will not ring with competing contractors.</li>
</ul>
<p>By using this site you agree to these terms and the applicable contractor or consumer agreement.</p>
<p><a href="/">Back to Home</a> | <a href="/privacy">Privacy</a> | <a href="/contractor_agreement">Contractor Agreement</a></p>
</div></div>
</body></html>"""

@app.route("/contractor_agreement")
def contractor_agreement():
    return f"""<!DOCTYPE html>
<html lang="en"><head><title>Contractor Agreement</title>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header"><h1>Contractor Agreement</h1></div>
<div class="container"><div class="card legal">
<p><strong>Albert R LaMotte dba Restoration Contractors MN</strong></p>
<p><strong>Last Updated:</strong> October 22, 2026</p>
<p>By creating an account you agree to the following:</p>
<ol>
<li>Leads are exclusive. You will be the only contractor who receives the homeowner’s contact information for that job.</li>
<li>You have 60 minutes from the time you claim a lead to accept or reject it. If you do not act, the lead is released.</li>
<li>You are not charged for a lead until you accept the assignment.</li>
<li>You will contact the homeowner promptly after acceptance and provide a professional quote.</li>
<li>You maintain any required Minnesota licenses and insurance for the services you offer.</li>
<li>This agreement is governed by the laws of the State of Minnesota.</li>
<li>No shared leads will be sold. Your phone will not receive calls from competing contractors on the same job.</li>
</ol>
<p>This agreement incorporates the Privacy Policy and Terms & Conditions.</p>
<p><a href="/">Back to Home</a> | <a href="/signup">Return to Signup</a></p>
</div></div>
</body></html>"""

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
