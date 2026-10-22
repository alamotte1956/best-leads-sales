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

@app.route("/")
def home():
    return """<!DOCTYPE html>
<html><head><title>Best Leads — Exclusive Twin Cities</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{font-family:system-ui,sans-serif;max-width:900px;margin:40px auto;padding:20px;background:#f8fafc;color:#0f172a}
.nav a{display:inline-block;margin:8px;padding:12px 18px;background:#0ea5e9;color:#fff;text-decoration:none;border-radius:8px;font-weight:600}
h1{margin-bottom:8px} .tag{color:#0369a1;font-weight:600}
</style></head><body>
<h1>Best Leads</h1>
<p class="tag">Exclusive leads. One contractor. No shared leads.</p>
<div class="nav">
<a href="/signup">Contractor Signup</a>
<a href="/contractor_login">Contractor Login</a>
<a href="/leads">Available Leads</a>
<a href="/admin_login">Admin</a>
<a href="/privacy">Privacy</a>
<a href="/terms">Terms</a>
</div>
</body></html>"""

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        try:
            with get_db() as db:
                if not request.form.get("agree"):
                    flash("You must agree to the Contractor Agreement.")
                    return redirect("/signup")
                db.execute("INSERT INTO contractors (name,email,phone,company,services,license_number,insurance,agreement_accepted,agreement_at) VALUES (?,?,?,?,?,?,?,1,CURRENT_TIMESTAMP)",
                           (request.form["name"], request.form["email"], request.form["phone"],
                            request.form.get("company",""), request.form.get("services",""),
                            request.form.get("license_number",""), request.form.get("insurance","")))
                db.commit()
            flash("Signed up. Log in now.")
            return redirect("/contractor_login")
        except:
            flash("Email already used.")
    return """<!DOCTYPE html>
<html><head><title>Signup</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font-family:system-ui;max-width:560px;margin:40px auto;padding:20px}input,textarea,button{width:100%;padding:12px;margin:6px 0;border:1px solid #cbd5e1;border-radius:8px;box-sizing:border-box}button{background:#0ea5e9;color:#fff;border:none;font-weight:600}</style>
</head><body>
<h1>Contractor Signup</h1>
<div style="border:1px solid #e2e8f0;padding:12px;margin:12px 0;background:#f8fafc;font-size:13px;border-radius:8px;white-space:pre-wrap">
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
   You agree to pay the stated price for each lead you accept. Stripe integration will be used for future billing.

8. Governing Law
   This agreement is governed by the laws of the State of Minnesota.
</div>
<label style="display:block;margin:10px 0"><input type="checkbox" name="agree" required> I agree to the Contractor Agreement</label>
<form method="post">
<input name="name" placeholder="Full name" required>
<input name="email" type="email" placeholder="Email" required>
<input name="phone" placeholder="Phone" required>
<input name="company" placeholder="Company">
<textarea name="services" placeholder="Services (Water Damage, Mold, Roofing...)"></textarea>
<input name="license_number" placeholder="MN License #">
<input name="insurance" placeholder="Insurance info">
<button>Create Account</button>
</form>
<p><a href="/">Home</a></p>
</body></html>"""

@app.route("/contractor_login", methods=["GET","POST"])
def contractor_login():
    if request.method == "POST":
        email = request.form.get("email","").strip()
        if email == ADMIN_EMAIL:
            session["is_admin"] = True
        with get_db() as db:
            c = db.execute("SELECT * FROM contractors WHERE email=? AND active=1", (email,)).fetchone()
            if c:
                session["contractor_id"] = c["id"]
                session["contractor_name"] = c["name"]
                return redirect("/leads")
            if email == ADMIN_EMAIL:
                return redirect("/admin")
        flash("Invalid login")
    return """<!DOCTYPE html>
<html><head><title>Login</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font-family:system-ui;max-width:480px;margin:60px auto;padding:20px}input,button{width:100%;padding:12px;margin:6px 0;border-radius:8px;border:1px solid #cbd5e1;box-sizing:border-box}button{background:#0ea5e9;color:#fff;border:none}</style>
</head><body>
<h1>Contractor Login</h1>
<form method="post"><input name="email" type="email" placeholder="Email" required><button>Login</button></form>
<p><a href="/signup">Sign up</a> · <a href="/">Home</a></p>
</body></html>"""

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/leads")
@login_required
def leads():
    with get_db() as db:
        avail = db.execute("SELECT * FROM leads WHERE status='available' ORDER BY id DESC").fetchall()
        mine = db.execute("SELECT * FROM leads WHERE assigned_to=? ORDER BY id DESC", (session["contractor_id"],)).fetchall()
    html = f"""<!DOCTYPE html>
<html><head><title>Leads</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{{font-family:system-ui;max-width:960px;margin:30px auto;padding:20px}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #e2e8f0;padding:10px;text-align:left}}.btn{{background:#0ea5e9;color:#fff;padding:6px 12px;border-radius:6px;text-decoration:none}}</style>
</head><body>
<h1>Exclusive Leads</h1>
<p>Hi {session.get('contractor_name')} · <a href="/logout">Logout</a></p>
<h2>Available</h2>
<table><tr><th>ID</th><th>Service</th><th>ZIP</th><th>Price</th><th></th></tr>"""
    for l in avail:
        html += f"<tr><td>{l['id']}</td><td>{l['service_type']}</td><td>{l['zip']}</td><td>${l['price']}</td><td><a class='btn' href='/buy/{l['id']}'>Buy</a></td></tr>"
    html += "</table><h2>My Leads</h2><table><tr><th>ID</th><th>Service</th><th>ZIP</th><th>Status</th></tr>"
    for l in mine:
        html += f"<tr><td>{l['id']}</td><td>{l['service_type']}</td><td>{l['zip']}</td><td>{l['status']}</td></tr>"
    html += "</table><p><a href='/'>Home</a></p></body></html>"
    return html

@app.route("/buy/<int:lid>")
@login_required
def buy(lid):
    with get_db() as db:
        lead = db.execute("SELECT * FROM leads WHERE id=? AND status='available'", (lid,)).fetchone()
        if lead:
            db.execute("UPDATE leads SET status='sold', assigned_to=? WHERE id=?", (session["contractor_id"], lid))
            db.execute("INSERT INTO assignments (lead_id, contractor_id, status) VALUES (?,?, 'accepted')", (lid, session["contractor_id"]))
            db.commit()
            flash(f"Lead #{lid} purchased")
        else:
            flash("Not available")
    return redirect("/leads")

@app.route("/privacy")
def privacy():
    return """<!DOCTYPE html><html><head><title>Privacy</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font-family:system-ui;max-width:760px;margin:40px auto;padding:20px;line-height:1.6}</style></head>
<body><h1>Privacy Policy</h1><p>Last updated: October 22, 2026</p>
<p>We collect contact information to match exclusive leads with one contractor. Data is shared only with the matched contractor. SMS is optional. Subject to Minnesota law.</p>
<p><a href="/">Home</a></p></body></html>"""

@app.route("/terms")
def terms():
    return """<!DOCTYPE html><html><head><title>Terms</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font-family:system-ui;max-width:760px;margin:40px auto;padding:20px;line-height:1.6}</style></head>
<body><h1>Terms & Conditions</h1><p>Last updated: October 22, 2026</p>
<ul><li>Exclusive leads only — no shared leads</li><li>Independent contractors</li><li>Minnesota law governs</li></ul>
<p><a href="/">Home</a></p></body></html>"""

@app.route("/admin_login", methods=["GET","POST"])
def admin_login():
    if request.method == "POST" and request.form.get("email")==ADMIN_EMAIL and request.form.get("password")==ADMIN_PASS:
        session["is_admin"] = True
        return redirect("/admin")
    return """<!DOCTYPE html><html><head><title>Admin</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font-family:system-ui;max-width:480px;margin:60px auto;padding:20px}input,button{width:100%;padding:12px;margin:6px 0;border-radius:8px;border:1px solid #cbd5e1;box-sizing:border-box}button{background:#0ea5e9;color:#fff;border:none}</style>
</head><body><h1>Admin Login</h1>
<form method="post"><input name="email" type="email" placeholder="Email"><input name="password" type="password" placeholder="Password"><button>Login</button></form></body></html>"""

@app.route("/admin")
@admin_required
def admin():
    with get_db() as db:
        c = db.execute("SELECT COUNT(*) n FROM contractors").fetchone()["n"]
        l = db.execute("SELECT COUNT(*) n FROM leads").fetchone()["n"]
        a = db.execute("SELECT COUNT(*) n FROM leads WHERE status='available'").fetchone()["n"]
    return f"""<!DOCTYPE html><html><head><title>Admin</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{{font-family:system-ui;max-width:800px;margin:40px auto;padding:20px}}a{{display:inline-block;margin:8px;padding:10px 16px;background:#0ea5e9;color:#fff;text-decoration:none;border-radius:8px}}</style>
</head><body>
<h1>Admin Dashboard</h1>
<p>Contractors: {c} · Leads: {l} · Available: {a}</p>
<a href="/seed">Seed Demo Data</a>
<a href="/assignments">Assignments</a>
<a href="/auto_match">Auto-Match</a>
<a href="/admin_logout">Logout</a>
</body></html>"""

@app.route("/admin_logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect("/")

@app.route("/seed")
@admin_required
def seed():
    services = ["Water Damage","Mold","Roofing","Siding","Windows","Bathroom","Kitchen","Additions","Drywall","Flooring"]
    zips = ["55331","55343","55344","55345","55346","55347","55391","55424","55435","55436","55437","55438","55439"]
    with get_db() as db:
        for i in range(40):
            try:
                db.execute("INSERT INTO contractors (name,email,phone,company,services,license_number,active) VALUES (?,?,?,?,?,?,1)",
                           (f"Contractor {i+1}", f"c{i+1}@demo.com", f"612-555-{1000+i:04d}", f"Co {i+1}",
                            random.choice(services), f"MN-{100000+i}"))
            except: pass
        for i in range(80):
            db.execute("INSERT INTO leads (name,phone,email,zip,service_type,details,status,price) VALUES (?,?,?,?,?,?,'available',45)",
                       (f"Homeowner {i+1}", f"612-555-{2000+i:04d}", f"h{i+1}@demo.com",
                        random.choice(zips), random.choice(services), "Demo job"))
        db.commit()
    return "<p>Seeded 40 contractors and 80 leads. <a href='/admin'>Back</a></p>"

@app.route("/assignments")
@admin_required
def assignments():
    with get_db() as db:
        rows = db.execute("""SELECT a.id, l.name ln, l.service_type, c.name cn, a.status, a.created
                             FROM assignments a JOIN leads l ON a.lead_id=l.id
                             JOIN contractors c ON a.contractor_id=c.id ORDER BY a.id DESC""").fetchall()
    html = "<html><body style='font-family:system-ui;max-width:900px;margin:40px auto;padding:20px'><h1>Assignments</h1><table border='1' cellpadding='8'><tr><th>ID</th><th>Lead</th><th>Service</th><th>Contractor</th><th>Status</th></tr>"
    for r in rows:
        html += f"<tr><td>{r['id']}</td><td>{r['ln']}</td><td>{r['service_type']}</td><td>{r['cn']}</td><td>{r['status']}</td></tr>"
    html += "</table><p><a href='/admin'>Back</a></p></body></html>"
    return html

@app.route("/auto_match")
@admin_required
def auto_match():
    matched = 0
    with get_db() as db:
        leads = db.execute("SELECT * FROM leads WHERE status='available'").fetchall()
        for lead in leads:
            c = db.execute("SELECT * FROM contractors WHERE active=1 AND services LIKE ? LIMIT 1", (f"%{lead['service_type']}%",)).fetchone()
            if c:
                db.execute("UPDATE leads SET status='assigned', assigned_to=? WHERE id=?", (c["id"], lead["id"]))
                db.execute("INSERT INTO assignments (lead_id, contractor_id, status) VALUES (?,?,'pending')", (lead["id"], c["id"]))
                matched += 1
        db.commit()
    return f"<p>Auto-matched {matched} leads. <a href='/assignments'>View</a> · <a href='/admin'>Admin</a></p>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
