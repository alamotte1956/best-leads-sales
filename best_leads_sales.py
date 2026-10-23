# COMPLETE_ATTRACTIVE_CONTRACTOR_SITE_V5_SERVICES_DROPDOWN_2026_10_22
from flask import Flask, request, redirect, url_for, session, flash, jsonify
import sqlite3, os, random
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")

DB = "leads.db"

SERVICES = [
    "Water Damage Restoration",
    "Mold Mitigation / Remediation",
    "Mold Inspection",
    "Dry Out Services",
    "Indoor Air Quality Testing",
    "Roofing",
    "Siding",
    "Windows",
    "Kitchen Remodeling",
    "Bathroom Remodeling",
    "Home Additions",
    "General Remodeling",
    "HVAC",
    "Plumbing",
    "Electrical",
    "Flooring",
    "Painting",
    "Other"
]

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
                active INTEGER DEFAULT 1,
                agreement_accepted INTEGER DEFAULT 0,
                agreement_at TIMESTAMP,
                password_hash TEXT,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, phone TEXT, email TEXT, zip TEXT,
                service_type TEXT, details TEXT, urgency TEXT,
                status TEXT DEFAULT 'available',
                assigned_to INTEGER,
                price REAL DEFAULT 45.0,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER, contractor_id INTEGER,
                status TEXT DEFAULT 'pending',
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        if db.execute("SELECT COUNT(*) FROM contractors").fetchone()[0] == 0:
            db.execute("""INSERT INTO contractors (name, email, phone, company, services, active, agreement_accepted)
                          VALUES (?, ?, ?, ?, ?, 1, 1)""",
                       ("Demo Contractor", "demo@example.com", "(612) 555-0100", "Demo Co", "Water Damage Restoration, Mold Mitigation / Remediation"))

init_db()

ADMIN_EMAIL = "alamotte1956@gmail.com"
ADMIN_PASS = "PeggySmith1$"

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

STYLE = """
:root { --blue: #0369a1; --blue2: #0284c7; --bg: #f1f5f9; --green: #059669; }
body { font-family: 'Segoe UI', system-ui, sans-serif; margin: 0; background: var(--bg); color: #0f172a; }
.header { background: linear-gradient(135deg, #0c4a6e, #0369a1); color: white; padding: 28px 20px; text-align: center; }
.header h1 { margin: 0; font-size: 2.1rem; letter-spacing: -0.5px; }
.header p { margin: 8px 0 0; opacity: 0.92; }
.nav { background: white; padding: 12px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.nav a { display: inline-block; margin: 6px; padding: 10px 16px; background: var(--blue); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; }
.nav a:hover { background: var(--blue2); }
.container { max-width: 960px; margin: 30px auto; padding: 0 16px; }
.card { background: white; border-radius: 14px; padding: 28px; box-shadow: 0 6px 20px rgba(0,0,0,0.06); margin-bottom: 20px; }
.note { background: #ecfdf5; color: #065f46; padding: 14px 16px; border-radius: 10px; font-weight: 600; border-left: 4px solid #10b981; margin-bottom: 16px; }
.red-note { background: #fef2f2; color: #991b1b; padding: 12px; border-radius: 8px; font-weight: 600; border-left: 4px solid #ef4444; }
input, textarea, select, button { width: 100%; padding: 12px; margin: 6px 0; border: 1px solid #cbd5e1; border-radius: 8px; box-sizing: border-box; font-size: 15px; }
button { background: var(--blue); color: white; border: none; font-weight: 600; cursor: pointer; }
button:hover { background: var(--blue2); }
button.green { background: var(--green); }
.agreement { white-space: pre-wrap; font-size: 14px; background: #f8fafc; border: 1px solid #e2e8f0; padding: 16px; border-radius: 10px; max-height: 300px; overflow: auto; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 10px; border-bottom: 1px solid #e2e8f0; }
select[multiple] { height: 140px; }
"""

@app.route("/")
def home():
    return f"""<!DOCTYPE html>
<html><head><title>Best Leads — Exclusive Twin Cities</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header">
  <h1>Best Leads</h1>
  <p>Exclusive Twin Cities Leads — One Contractor Per Job</p>
</div>
<div class="nav">
  <a href="/signup">Contractor Signup</a>
  <a href="/available_leads">Available Leads</a>
  <a href="/contractor_login">Login</a>
  <a href="/admin">Admin</a>
  <a href="/privacy">Privacy</a>
  <a href="/terms">Terms</a>
</div>
<div class="container">
  <div class="note">No shared leads. Your phone will not ring with competing contractors.</div>
  <div class="card">
    <h2>Professional Exclusive Lead Portal</h2>
    <p>High-quality, exclusive homeowner leads for Twin Cities contractors. Attractive, mobile-friendly design. Leads expire after 24 hours if not accepted.</p>
    <p><strong>First 5 leads 50% off until 11/30/2026</strong> for new contractors.</p>
  </div>
</div>
</body></html>"""

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        if not request.form.get("agree"):
            flash("You must agree to the Contractor Agreement.")
            return redirect("/signup")
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        company = request.form.get("company", "")
        services_list = request.form.getlist("services")
        services = ", ".join(services_list) if services_list else ""
        license_number = request.form.get("license_number", "")
        insurance = request.form.get("insurance", "")
        with get_db() as db:
            try:
                db.execute("""INSERT INTO contractors (name, email, phone, company, services, license_number, insurance, agreement_accepted, agreement_at)
                              VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)""",
                           (name, email, phone, company, services, license_number, insurance, datetime.utcnow()))
                flash("Account created. Please log in.")
                return redirect("/contractor_login")
            except sqlite3.IntegrityError:
                flash("Email already registered.")
                return redirect("/signup")
    options = "".join([f'<option value="{s}">{s}</option>' for s in SERVICES])
    return f"""<!DOCTYPE html>
<html><head><title>Contractor Signup</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header"><h1>Contractor Signup</h1></div>
<div class="container">
  <div class="card">
    <div class="agreement">CONTRACTOR AGREEMENT
Albert R LaMotte dba: Restoration Contractors MN
(Subject to Minnesota Law)

By signing up you agree:

1. Independent Contractor
   You are an independent contractor, not an employee of Restoration Contractors MN.

2. Exclusive Leads
   Leads you purchase are exclusive. You are the only contractor who receives the homeowner’s contact information for that lead.

3. Licensing
   You represent that you hold all licenses required by Minnesota law for the services you offer and that you will maintain them in good standing.

4. Insurance
   You are solely responsible for carrying adequate liability and workers’ compensation insurance. We do not verify insurance.

5. Home Solicitation Sales Act
   If you visit a homeowner as a result of a lead, you are responsible for complying with the Minnesota Home Solicitation Sales Act (Minn. Stat. §§ 325G.06–325G.10), including providing any required cancellation notice.

6. No Shared Leads
   You will not share or resell any lead obtained through this platform.

7. Payment
   You agree to pay the stated price for each lead you accept. First 5 leads 50% off until 11/30/2026 for new accounts.

8. Governing Law
   This agreement is governed by the laws of the State of Minnesota.</div>
    <form method="post">
      <label style="display:block;margin:12px 0"><input type="checkbox" name="agree" required style="width:auto"> I agree to the Contractor Agreement</label>
      <input name="name" placeholder="Full name" required>
      <input name="email" type="email" placeholder="Email" required>
      <input name="password" type="password" placeholder="Password" required>
      <input name="phone" placeholder="Phone" required>
      <input name="company" placeholder="Company">
      <label style="display:block; margin-top:12px; font-weight:600;">Services Offered (hold Ctrl/Cmd to select multiple)</label>
      <select name="services" multiple required>
        {options}
      </select>
      <input name="license_number" placeholder="MN License # (optional)">
      <input name="insurance" placeholder="Insurance info (optional)">
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
<html><head><title>Login</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header"><h1>Contractor Login</h1></div>
<div class="container">
  <div class="card">
    <form method="post">
      <input name="email" type="email" placeholder="Email" required>
      <input name="password" type="password" placeholder="Password" required>
      <button>Login</button>
    </form>
  </div>
</div>
</body></html>"""

@app.route("/available_leads")
@login_required
def available_leads():
    with get_db() as db:
        leads = db.execute("SELECT * FROM leads WHERE status='available' ORDER BY created DESC").fetchall()
    rows = ""
    for lead in leads:
        rows += f"""<tr>
            <td>{lead['service_type']}</td>
            <td>{lead['zip']}</td>
            <td>${lead['price']:.0f}</td>
            <td><form method="post" action="/buy/{lead['id']}"><button class="green">Buy Exclusive Lead</button></form></td>
        </tr>"""
    if not rows:
        rows = "<tr><td colspan='4'>No available leads right now.</td></tr>"
    return f"""<!DOCTYPE html>
<html><head><title>Available Leads</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header"><h1>Available Exclusive Leads</h1></div>
<div class="nav"><a href="/">Home</a> <a href="/logout">Logout</a></div>
<div class="container">
  <div class="note">No shared leads. One contractor per job.</div>
  <div class="red-note">Leads expire after 24 hours of not being accepted.</div>
  <div class="card">
    <p>Welcome {session.get('contractor_name', 'Contractor')}</p>
    <table>
      <tr><th>Service</th><th>Zip</th><th>Price</th><th>Action</th></tr>
      {rows}
    </table>
  </div>
</div>
</body></html>"""

@app.route("/buy/<int:lead_id>", methods=["POST"])
@login_required
def buy(lead_id):
    cid = session["contractor_id"]
    with get_db() as db:
        db.execute("UPDATE leads SET status='assigned', assigned_to=? WHERE id=? AND status='available'", (cid, lead_id))
        db.execute("INSERT INTO assignments (lead_id, contractor_id, status) VALUES (?, ?, 'accepted')", (lead_id, cid))
    flash("Lead purchased. Contact info will appear in your account.")
    return redirect("/available_leads")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/admin")
@admin_required
def admin():
    with get_db() as db:
        contractors = db.execute("SELECT * FROM contractors").fetchall()
        leads = db.execute("SELECT * FROM leads").fetchall()
    c_rows = "".join([f"<tr><td>{c['name']}</td><td>{c['email']}</td><td>{c['services'] or ''}</td><td>{c['active']}</td></tr>" for c in contractors])
    l_rows = "".join([f"<tr><td>{l['name']}</td><td>{l['service_type']}</td><td>{l['status']}</td><td>${l['price']}</td></tr>" for l in leads])
    return f"""<!DOCTYPE html>
<html><head><title>Admin</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header"><h1>Admin Dashboard</h1></div>
<div class="container">
  <div class="card">
    <h3>Contractors</h3>
    <table><tr><th>Name</th><th>Email</th><th>Services</th><th>Active</th></tr>{c_rows}</table>
  </div>
  <div class="card">
    <h3>Leads</h3>
    <table><tr><th>Name</th><th>Service</th><th>Status</th><th>Price</th></tr>{l_rows}</table>
  </div>
</div>
</body></html>"""

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("email") == ADMIN_EMAIL and request.form.get("password") == ADMIN_PASS:
            session["is_admin"] = True
            return redirect("/admin")
    return f"""<!DOCTYPE html>
<html><head><title>Admin Login</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header"><h1>Admin Login</h1></div>
<div class="container">
  <div class="card">
    <form method="post">
      <input name="email" type="email" placeholder="Email" required>
      <input name="password" type="password" placeholder="Password" required>
      <button>Login</button>
    </form>
  </div>
</div>
</body></html>"""

@app.route("/privacy")
def privacy():
    return f"""<!DOCTYPE html>
<html><head><title>Privacy</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header"><h1>Privacy Policy</h1></div>
<div class="container"><div class="card">
<p>We collect contractor and lead information solely to operate the exclusive lead matching service. We do not share leads with multiple contractors. SMS and email notifications are sent only for lead assignment and account purposes.</p>
<p><a href="/">Back</a></p>
</div></div>
</body></html>"""

@app.route("/terms")
def terms():
    return f"""<!DOCTYPE html>
<html><head><title>Terms</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header"><h1>Terms & Conditions</h1></div>
<div class="container"><div class="card">
<p>Exclusive leads only. Minnesota law governs. Independent contractors are responsible for their own licensing, insurance, and compliance with the Minnesota Home Solicitation Sales Act (Minn. Stat. §§ 325G.06–325G.10). Leads expire after 24 hours if not accepted.</p>
<p><a href="/">Back</a></p>
</div></div>
</body></html>"""

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
