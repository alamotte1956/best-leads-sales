# FORCE_UPDATE_2026_10_22_ATTRACTIVE_CONTRACTOR_SITE
from flask import Flask, request, redirect, url_for, session, flash
import sqlite3, os, random
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me")

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
                services TEXT, license_number TEXT, insurance TEXT,
                active INTEGER DEFAULT 1, 
                agreement_accepted INTEGER DEFAULT 0,
                agreement_at TIMESTAMP,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, phone TEXT, email TEXT, zip TEXT,
                service_type TEXT, details TEXT,
                status TEXT DEFAULT 'available',
                assigned_to INTEGER, price REAL DEFAULT 45,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER, contractor_id INTEGER,
                status TEXT DEFAULT 'pending',
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

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

BASE_STYLE = """
body { font-family: system-ui, sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; background: #f8fafc; color: #0f172a; }
.nav a { display: inline-block; margin: 8px; padding: 12px 18px; background: #0ea5e9; color: #fff; text-decoration: none; border-radius: 8px; font-weight: 600; }
h1 { margin-bottom: 12px; }
.card { background: white; padding: 24px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin: 20px 0; }
input, textarea, select, button { width: 100%; padding: 12px; margin: 6px 0; border: 1px solid #cbd5e1; border-radius: 8px; box-sizing: border-box; }
button { background: #0ea5e9; color: white; border: none; font-weight: 600; cursor: pointer; }
button:hover { background: #0284c7; }
.note { background: #fef3c7; padding: 12px; border-radius: 8px; margin: 12px 0; font-weight: 600; }
"""

@app.route("/")
def home():
    return f"""<!DOCTYPE html>
<html><head><title>Best Leads — Exclusive Twin Cities</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{BASE_STYLE}</style></head><body>
<div class="nav">
  <a href="/signup">Contractor Signup</a>
  <a href="/available_leads">Available Leads</a>
  <a href="/contractor_login">Login</a>
  <a href="/admin">Admin</a>
  <a href="/privacy">Privacy</a>
  <a href="/terms">Terms</a>
</div>
<h1>Best Leads — Exclusive Twin Cities Leads</h1>
<div class="note">No shared leads. One contractor per job.</div>
<p>Attractive, professional contractor portal. Exclusive leads only.</p>
</body></html>"""

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        if not request.form.get("agree"):
            flash("You must agree to the Contractor Agreement.")
            return redirect("/signup")
        # Insert logic would go here
        flash("Account created. Please log in.")
        return redirect("/contractor_login")
    return f"""<!DOCTYPE html>
<html><head><title>Contractor Signup</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{BASE_STYLE}</style></head><body>
<h1>Contractor Signup</h1>
<div class="card">
<div style="white-space:pre-wrap; font-size:14px; border:1px solid #e2e8f0; padding:12px; background:#f8fafc; border-radius:8px;">
CONTRACTOR AGREEMENT
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
   You agree to pay the stated price for each lead you accept.

8. Governing Law
   This agreement is governed by the laws of the State of Minnesota.
</div>
<form method="post">
<label style="display:block;margin:10px 0"><input type="checkbox" name="agree" required style="width:auto"> I agree to the Contractor Agreement</label>
<input name="name" placeholder="Full name" required>
<input name="email" type="email" placeholder="Email" required>
<input name="password" type="password" placeholder="Password" required>
<input name="phone" placeholder="Phone" required>
<input name="company" placeholder="Company">
<textarea name="services" placeholder="Services (Water Damage, Mold, Roofing...)"></textarea>
<input name="license_number" placeholder="MN License #">
<input name="insurance" placeholder="Insurance info">
<button>Create Account</button>
</form>
</div>
</body></html>"""

@app.route("/contractor_login", methods=["GET", "POST"])
def contractor_login():
    if request.method == "POST":
        # Login logic placeholder
        session["contractor_id"] = 1
        session["contractor_name"] = "Demo Contractor"
        return redirect("/available_leads")
    return f"""<!DOCTYPE html>
<html><head><title>Login</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{BASE_STYLE}</style></head><body>
<h1>Contractor Login</h1>
<div class="card">
<form method="post">
<input name="email" type="email" placeholder="Email" required>
<input name="password" type="password" placeholder="Password" required>
<button>Login</button>
</form>
</div>
</body></html>"""

@app.route("/available_leads")
@login_required
def available_leads():
    return f"""<!DOCTYPE html>
<html><head><title>Available Leads</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{BASE_STYLE}</style></head><body>
<div class="nav"><a href="/">Home</a> <a href="/logout">Logout</a></div>
<h1>Available Exclusive Leads</h1>
<div class="note">No shared leads. One contractor per job.</div>
<p>Welcome {session.get('contractor_name', 'Contractor')}</p>
<div class="card">No available leads right now (demo).</div>
</body></html>"""

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/admin")
@admin_required
def admin():
    return f"""<!DOCTYPE html>
<html><head><title>Admin</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{BASE_STYLE}</style></head><body>
<h1>Admin Dashboard</h1>
<div class="card">Admin area — attractive version loaded.</div>
</body></html>"""

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("email") == ADMIN_EMAIL and request.form.get("password") == ADMIN_PASS:
            session["is_admin"] = True
            return redirect("/admin")
        flash("Invalid credentials")
    return f"""<!DOCTYPE html>
<html><head><title>Admin Login</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{BASE_STYLE}</style></head><body>
<h1>Admin Login</h1>
<div class="card">
<form method="post">
<input name="email" type="email" placeholder="Email" required>
<input name="password" type="password" placeholder="Password" required>
<button>Login</button>
</form>
</div>
</body></html>"""

@app.route("/privacy")
def privacy():
    return f"""<!DOCTYPE html>
<html><head><title>Privacy</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{BASE_STYLE}</style></head><body>
<h1>Privacy Policy</h1>
<div class="card">
<p>We collect contractor and lead information solely to operate the exclusive lead matching service. We do not share leads with multiple contractors.</p>
<p><a href="/">Back</a></p>
</div>
</body></html>"""

@app.route("/terms")
def terms():
    return f"""<!DOCTYPE html>
<html><head><title>Terms</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{BASE_STYLE}</style></head><body>
<h1>Terms & Conditions</h1>
<div class="card">
<p>Exclusive leads only. Minnesota law governs. Independent contractors are responsible for their own licensing, insurance, and compliance with the Minnesota Home Solicitation Sales Act.</p>
<p><a href="/">Back</a></p>
</div>
</body></html>"""

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
