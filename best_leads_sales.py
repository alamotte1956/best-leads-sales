# FULL CONTRACTOR SITE - Restored signup fields + working login + blue/orange style
from flask import Flask, request, redirect, url_for, session, flash
import sqlite3, os, random
from datetime import datetime, timedelta
from functools import wraps

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
        "55364","55369","55391","55416","55424","55435","55436","55437","55438","55439"]

def get_db():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS contractors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, email TEXT UNIQUE, password TEXT, phone TEXT, company TEXT,
            license_number TEXT, services TEXT, service_zips TEXT,
            has_insurance TEXT, insurance_notes TEXT,
            agreement_accepted INTEGER DEFAULT 0, agreement_at TEXT,
            active INTEGER DEFAULT 1, created TEXT
        );
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, phone TEXT, email TEXT, service TEXT, zip TEXT,
            details TEXT, urgency TEXT, budget TEXT, created TEXT, status TEXT DEFAULT 'new',
            assigned_to INTEGER, accepted_at TEXT, expires_at TEXT, price REAL DEFAULT 75.0
        );
        """)
        db.commit()

init_db()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "contractor_id" not in session:
            flash("Please log in.")
            return redirect("/contractor_login")
        return f(*args, **kwargs)
    return decorated

STYLE = """
body { font-family: system-ui, sans-serif; background:#f8fafc; margin:0; color:#0f172a; }
.header { background: linear-gradient(135deg, #0c4a6e, #0369a1); color:white; padding:28px 20px; text-align:center; }
.nav { background:#1e293b; padding:12px; text-align:center; }
.nav a { color:white; margin:0 12px; text-decoration:none; font-weight:500; }
.container { max-width:900px; margin:20px auto; padding:0 16px; }
.card { background:white; border-radius:12px; padding:24px; box-shadow:0 2px 8px rgba(0,0,0,0.06); margin-bottom:16px; }
input, select, textarea { width:100%; padding:12px; margin:8px 0; border:1px solid #cbd5e1; border-radius:8px; box-sizing:border-box; }
label { font-weight:600; display:block; margin-top:12px; }
button { background:#f97316; color:white; border:none; padding:14px 20px; border-radius:8px; font-weight:600; cursor:pointer; width:100%; }
button:hover { background:#ea580c; }
.lead-card { border-left:4px solid #0ea5e9; }
.flash { background:#fef3c7; padding:12px; border-radius:8px; margin-bottom:12px; }
"""

@app.route("/")
def home():
    return f"""<!DOCTYPE html><html><head><title>Best Leads — Exclusive Twin Cities</title>
    <meta name="viewport" content="width=device-width,initial-scale=1"><style>{STYLE}</style></head><body>
    <div class="header"><h1>Best Leads — Exclusive Twin Cities</h1>
    <p>No shared leads. One contractor per job.</p></div>
    <div class="nav"><a href="/">Home</a><a href="/signup">Sign Up</a><a href="/contractor_login">Login</a>
    <a href="/available_leads">Available Leads</a></div>
    <div class="container"><div class="card">
    <h2>Exclusive Leads for Twin Cities Contractors</h2>
    <p>Get matched with homeowners who need restoration, remodeling, roofing, and more. Each lead is exclusive — only one contractor receives it.</p>
    <p><a href="/signup"><button>Join as a Contractor</button></a></p>
    </div></div></body></html>"""

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        phone = request.form.get("phone", "").strip()
        company = request.form.get("company", "").strip()
        license_number = request.form.get("license_number", "").strip()
        services_list = request.form.getlist("services")
        services = ", ".join(services_list) if services_list else ""
        service_zips = request.form.get("service_zips", "").strip()
        has_insurance = request.form.get("has_insurance", "No")
        insurance_notes = request.form.get("insurance_notes", "").strip()
        if not name or not email or not password:
            flash("Name, email, and password are required.")
            return redirect("/signup")
        with get_db() as db:
            try:
                db.execute("""INSERT INTO contractors 
                    (name, email, password, phone, company, license_number, services, service_zips,
                     has_insurance, insurance_notes, agreement_accepted, agreement_at, created)
                    VALUES (?,?,?,?,?,?,?,?,?,?,1,?,?)""",
                    (name, email, password, phone, company, license_number, services, service_zips,
                     has_insurance, insurance_notes, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
                db.commit()
                flash("Account created. Please log in.")
                return redirect("/contractor_login")
            except sqlite3.IntegrityError:
                flash("That email is already registered.")
                return redirect("/signup")
    options = "".join([f'<option value="{s}">{s}</option>' for s in SERVICES])
    zip_options = "".join([f'<option value="{z}">{z}</option>' for z in ZIPS])
    return f"""<!DOCTYPE html><html><head><title>Contractor Signup</title>
    <meta name="viewport" content="width=device-width,initial-scale=1"><style>{STYLE}</style></head><body>
    <div class="header"><h1>Contractor Signup</h1><p>Exclusive Twin Cities leads. No shared jobs.</p></div>
    <div class="nav"><a href="/">Home</a><a href="/contractor_login">Already have an account?</a></div>
    <div class="container"><div class="card">
    <form method="post">
      <label>Full Name *</label><input name="name" required>
      <label>Email *</label><input name="email" type="email" required>
      <label>Password *</label><input name="password" type="password" required>
      <label>Phone *</label><input name="phone" required>
      <label>Company Name</label><input name="company">
      <label>Minnesota License Number</label><input name="license_number" placeholder="e.g. BC123456">
      <label>Services Offered (hold Ctrl/Cmd to select multiple) *</label>
      <select name="services" multiple size="6" required>{options}</select>
      <label>Service Area ZIPs (hold Ctrl/Cmd to select multiple)</label>
      <select name="service_zips" multiple size="5">{zip_options}</select>
      <label>Do you carry liability insurance?</label>
      <select name="has_insurance"><option>Yes</option><option>No</option><option>Pending</option></select>
      <label>Insurance Notes (carrier, policy #, or expiration)</label>
      <textarea name="insurance_notes" rows="2"></textarea>
      <label style="font-weight:normal; margin:16px 0;">
        <input type="checkbox" name="agree" required style="width:auto; margin-right:8px;">
        I agree to the Contractor Agreement, exclusive lead terms, and Minnesota law.
      </label>
      <button type="submit">Create Account</button>
    </form>
    </div></div></body></html>"""

@app.route("/contractor_login", methods=["GET", "POST"])
def contractor_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with get_db() as db:
            c = db.execute("SELECT * FROM contractors WHERE email=?", (email,)).fetchone()
            if c and c["password"] == password:
                session["contractor_id"] = c["id"]
                session["contractor_name"] = c["name"]
                return redirect("/available_leads")
        flash("Invalid email or password.")
    return f"""<!DOCTYPE html><html><head><title>Login</title>
    <meta name="viewport" content="width=device-width,initial-scale=1"><style>{STYLE}</style></head><body>
    <div class="header"><h1>Contractor Login</h1></div>
    <div class="nav"><a href="/">Home</a><a href="/signup">Sign Up</a></div>
    <div class="container"><div class="card">
    <form method="post">
      <label>Email</label><input name="email" type="email" required>
      <label>Password</label><input name="password" type="password" required>
      <button>Login</button>
    </form>
    </div></div></body></html>"""

@app.route("/available_leads")
@login_required
def available_leads():
    now = datetime.utcnow()
    with get_db() as db:
        leads = db.execute("""SELECT * FROM leads WHERE status='new' AND (expires_at IS NULL OR expires_at > ?)
                              ORDER BY created DESC""", (now.isoformat(),)).fetchall()
    cards = ""
    for lead in leads:
        cards += f"""<div class="card lead-card">
        <strong>{lead['service']}</strong> — ZIP {lead['zip']}<br>
        Urgency: {lead['urgency']} | Budget: {lead['budget']}<br>
        Price: ${lead['price']}<br>
        <form method="post" action="/claim/{lead['id']}"><button>Claim This Lead</button></form>
        </div>"""
    if not cards:
        cards = "<div class='card'>No available leads right now.</div>"
    return f"""<!DOCTYPE html><html><head><title>Available Leads</title>
    <style>{STYLE}</style></head><body>
    <div class="header"><h1>Available Exclusive Leads</h1></div>
    <div class="nav"><a href="/">Home</a><a href="/my_assignments">My Assignments</a><a href="/logout">Logout</a></div>
    <div class="container">{cards}</div></body></html>"""

@app.route("/claim/<int:lead_id>", methods=["POST"])
@login_required
def claim(lead_id):
    cid = session["contractor_id"]
    now = datetime.utcnow()
    expires = (now + timedelta(hours=24)).isoformat()
    with get_db() as db:
        db.execute("""UPDATE leads SET status='assigned', assigned_to=?, expires_at=? WHERE id=? AND status='new'""",
                   (cid, expires, lead_id))
        db.commit()
    flash("Lead claimed. You have 24 hours to accept or reject.")
    return redirect("/my_assignments")

@app.route("/my_assignments")
@login_required
def my_assignments():
    cid = session["contractor_id"]
    with get_db() as db:
        leads = db.execute("SELECT * FROM leads WHERE assigned_to=? AND status='assigned'", (cid,)).fetchall()
    cards = ""
    for lead in leads:
        cards += f"""<div class="card lead-card">
        <strong>{lead['service']}</strong> — ZIP {lead['zip']}<br>
        {lead['details'] or ''}<br>
        <form method="post" action="/respond/{lead['id']}">
          <button name="action" value="accept">Accept</button>
          <button name="action" value="reject" style="background:#64748b; margin-top:8px;">Reject</button>
        </form></div>"""
    if not cards:
        cards = "<div class='card'>No pending assignments.</div>"
    return f"""<!DOCTYPE html><html><head><title>My Assignments</title><style>{STYLE}</style></head><body>
    <div class="header"><h1>My Assignments</h1></div>
    <div class="nav"><a href="/available_leads">Available Leads</a><a href="/logout">Logout</a></div>
    <div class="container">{cards}</div></body></html>"""

@app.route("/respond/<int:lead_id>", methods=["POST"])
@login_required
def respond(lead_id):
    action = request.form.get("action")
    cid = session["contractor_id"]
    with get_db() as db:
        if action == "accept":
            db.execute("UPDATE leads SET status='accepted', accepted_at=? WHERE id=? AND assigned_to=?",
                       (datetime.utcnow().isoformat(), lead_id, cid))
            flash("Lead accepted. Contact info is now available.")
        else:
            db.execute("UPDATE leads SET status='new', assigned_to=NULL, expires_at=NULL WHERE id=? AND assigned_to=?",
                       (lead_id, cid))
            flash("Lead rejected and returned to the pool.")
        db.commit()
    return redirect("/my_assignments")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/seed_demo")
def seed_demo():
    with get_db() as db:
        for i in range(1, 6):
            try:
                db.execute("""INSERT INTO contractors (name, email, password, phone, company, services, active, created)
                              VALUES (?,?,?,?,?,?,1,?)""",
                           (f"Demo Contractor {i}", f"demo{i}@example.com", "demo123",
                            f"612-555-00{i:02d}", f"Demo Co {i}", "Roofing, Water Damage Restoration",
                            datetime.utcnow().isoformat()))
            except sqlite3.IntegrityError:
                pass
        services = random.choices(SERVICES, k=10)
        for i in range(10):
            db.execute("""INSERT INTO leads (name, phone, email, service, zip, details, urgency, budget, created, status, price)
                          VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                       (f"Homeowner {i+1}", f"612-555-{1000+i}", f"home{i}@example.com",
                        services[i], random.choice(ZIPS), "Need help soon", 
                        random.choice(["Urgent","This week","Flexible"]),
                        random.choice(["Under $5k","$5k–$15k","$15k+"]),
                        datetime.utcnow().isoformat(), "new", random.choice([65,75,95])))
        db.commit()
    flash("Demo data seeded. Log in with demo1@example.com / demo123")
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
