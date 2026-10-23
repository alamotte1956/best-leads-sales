# ATTRACTIVE_UPDATE_V3_2026_10_22
from flask import Flask, request, redirect, url_for, session, flash
import sqlite3, os
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

STYLE = """
:root { --blue: #0369a1; --blue2: #0284c7; --bg: #f1f5f9; }
body { font-family: 'Segoe UI', system-ui, sans-serif; margin: 0; background: var(--bg); color: #0f172a; }
.header { background: linear-gradient(135deg, #0c4a6e, #0369a1); color: white; padding: 28px 20px; text-align: center; }
.header h1 { margin: 0; font-size: 2rem; letter-spacing: -0.5px; }
.header p { margin: 8px 0 0; opacity: 0.9; }
.nav { background: white; padding: 12px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.nav a { display: inline-block; margin: 6px; padding: 10px 16px; background: var(--blue); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; }
.nav a:hover { background: var(--blue2); }
.container { max-width: 920px; margin: 30px auto; padding: 0 16px; }
.card { background: white; border-radius: 14px; padding: 28px; box-shadow: 0 6px 20px rgba(0,0,0,0.06); margin-bottom: 20px; }
.note { background: #ecfdf5; color: #065f46; padding: 14px 16px; border-radius: 10px; font-weight: 600; border-left: 4px solid #10b981; }
input, textarea, select, button { width: 100%; padding: 12px; margin: 6px 0; border: 1px solid #cbd5e1; border-radius: 8px; box-sizing: border-box; font-size: 15px; }
button { background: var(--blue); color: white; border: none; font-weight: 600; cursor: pointer; }
button:hover { background: var(--blue2); }
.agreement { white-space: pre-wrap; font-size: 14px; background: #f8fafc; border: 1px solid #e2e8f0; padding: 16px; border-radius: 10px; max-height: 280px; overflow: auto; }
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
    <p>High-quality, exclusive homeowner leads for Twin Cities contractors. Attractive, mobile-friendly design.</p>
  </div>
</div>
</body></html>"""

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        if not request.form.get("agree"):
            flash("You must agree to the Contractor Agreement.")
            return redirect("/signup")
        flash("Account created. Please log in.")
        return redirect("/contractor_login")
    return f"""<!DOCTYPE html>
<html><head><title>Contractor Signup</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header"><h1>Contractor Signup</h1></div>
<div class="container">
  <div class="card">
    <div class="agreement">CONTRACTOR AGREEMENT
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
   This agreement is governed by the laws of the State of Minnesota.</div>
    <form method="post">
      <label style="display:block;margin:12px 0"><input type="checkbox" name="agree" required style="width:auto"> I agree to the Contractor Agreement</label>
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
</div>
</body></html>"""

@app.route("/contractor_login", methods=["GET", "POST"])
def contractor_login():
    if request.method == "POST":
        session["contractor_id"] = 1
        session["contractor_name"] = "Demo Contractor"
        return redirect("/available_leads")
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
    return f"""<!DOCTYPE html>
<html><head><title>Available Leads</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header"><h1>Available Exclusive Leads</h1></div>
<div class="nav"><a href="/">Home</a> <a href="/logout">Logout</a></div>
<div class="container">
  <div class="note">No shared leads. One contractor per job.</div>
  <div class="card">
    <p>Welcome {session.get('contractor_name', 'Contractor')}</p>
    <p>No available leads right now (demo).</p>
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
    return f"""<!DOCTYPE html>
<html><head><title>Admin</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{STYLE}</style></head><body>
<div class="header"><h1>Admin Dashboard</h1></div>
<div class="container"><div class="card">Admin area — attractive v3 loaded.</div></div>
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
<p>We collect contractor and lead information solely to operate the exclusive lead matching service. We do not share leads with multiple contractors.</p>
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
<p>Exclusive leads only. Minnesota law governs. Independent contractors are responsible for their own licensing, insurance, and compliance with the Minnesota Home Solicitation Sales Act.</p>
<p><a href="/">Back</a></p>
</div></div>
</body></html>"""

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
