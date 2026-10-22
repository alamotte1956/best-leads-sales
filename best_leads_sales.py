from flask import Flask, render_template_string, request, redirect, url_for, session, flash
import sqlite3, os, random
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")

DB_PATH = "best_leads.db"

def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS contractors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, email TEXT UNIQUE, phone TEXT, company TEXT,
                services TEXT, license_number TEXT, insurance TEXT,
                active INTEGER DEFAULT 1, created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, phone TEXT, email TEXT, zip TEXT,
                service_type TEXT, details TEXT,
                status TEXT DEFAULT 'available',
                assigned_to INTEGER, price REAL DEFAULT 45.0,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                assigned_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER, contractor_id INTEGER,
                status TEXT DEFAULT 'pending',
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

init_db()

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "alamotte1956@gmail.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "PeggySmith1$")

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "contractor_id" not in session:
            return redirect(url_for("contractor_login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html><head><title>Best Leads Sales</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>body{font-family:Arial;max-width:800px;margin:40px auto;padding:20px;} a{display:inline-block;margin:10px;padding:12px 20px;background:#0ea5e9;color:white;text-decoration:none;border-radius:6px;}</style>
    </head><body>
    <h1>Best Leads — Exclusive Twin Cities Leads</h1>
    <p>No shared leads. One contractor per job.</p>
    <a href="/signup">Contractor Signup</a>
    <a href="/contractor_login">Contractor Login</a>
    <a href="/leads">Available Leads</a>
    <a href="/admin_login">Admin</a>
    <a href="/privacy">Privacy</a>
    <a href="/terms">Terms</a>
    </body></html>
    """

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        with get_db() as db:
            try:
                db.execute("INSERT INTO contractors (name,email,phone,company,services,license_number,insurance) VALUES (?,?,?,?,?,?,?)",
                    (request.form.get("name"), request.form.get("email"), request.form.get("phone"),
                     request.form.get("company"), request.form.get("services"),
                     request.form.get("license_number"), request.form.get("insurance")))
                db.commit()
                flash("Signup successful.")
                return redirect(url_for("contractor_login"))
            except sqlite3.IntegrityError:
                flash("Email already registered.")
    return """
    <!DOCTYPE html><html><head><title>Signup</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>body{font-family:Arial;max-width:600px;margin:40px auto;padding:20px;} input,textarea{width:100%;padding:10px;margin:6px 0;border:1px solid #ccc;border-radius:4px;} button{background:#0ea5e9;color:white;padding:12px 24px;border:none;border-radius:6px;}</style>
    </head><body>
    <h1>Contractor Signup</h1>
    <form method="post">
        <input name="name" placeholder="Full Name" required>
        <input name="email" type="email" placeholder="Email" required>
        <input name="phone" placeholder="Phone" required>
        <input name="company" placeholder="Company">
        <textarea name="services" placeholder="Services (water damage, mold, roofing, etc.)"></textarea>
        <input name="license_number" placeholder="MN License #">
        <input name="insurance" placeholder="Insurance info">
        <button>Sign Up</button>
    </form>
    <p><a href="/">Home</a></p>
    </body></html>
    """

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
                return redirect(url_for("leads"))
            if email == ADMIN_EMAIL:
                return redirect(url_for("admin"))
        flash("Invalid login.")
    return """
    <!DOCTYPE html><html><head><title>Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>body{font-family:Arial;max-width:500px;margin:40px auto;padding:20px;} input{width:100%;padding:10px;margin:6px 0;border:1px solid #ccc;border-radius:4px;} button{background:#0ea5e9;color:white;padding:12px 24px;border:none;border-radius:6px;}</style>
    </head><body>
    <h1>Contractor Login</h1>
    <form method="post"><input name="email" type="email" placeholder="Email" required><button>Login</button></form>
    <p><a href="/signup">Sign up</a> | <a href="/">Home</a></p>
    </body></html>
    """

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/leads")
@login_required
def leads():
    with get_db() as db:
        available = db.execute("SELECT * FROM leads WHERE status='available' ORDER BY created DESC").fetchall()
        mine = db.execute("SELECT * FROM leads WHERE assigned_to=? ORDER BY created DESC", (session["contractor_id"],)).fetchall()
    html = f"""
    <!DOCTYPE html><html><head><title>Leads</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>body{{font-family:Arial;max-width:900px;margin:40px auto;padding:20px;}} table{{width:100%;border-collapse:collapse;}} th,td{{border:1px solid #ddd;padding:8px;}} .btn{{background:#0ea5e9;color:white;padding:6px 12px;text-decoration:none;border-radius:4px;}}</style>
    </head><body>
    <h1>Available Exclusive Leads</h1>
    <p>Welcome {session.get('contractor_name')} | <a href="/logout">Logout</a></p>
    <h2>Available</h2>
    <table><tr><th>ID</th><th>Service</th><th>ZIP</th><th>Price</th><th></th></tr>
    """
    for l in available:
        html += f"<tr><td>{l['id']}</td><td>{l['service_type']}</td><td>{l['zip']}</td><td>${l['price']}</td><td><a class='btn' href='/buy/{l['id']}'>Buy</a></td></tr>"
    html += "</table><h2>My Leads</h2><table><tr><th>ID</th><th>Service</th><th>ZIP</th><th>Status</th></tr>"
    for l in mine:
        html += f"<tr><td>{l['id']}</td><td>{l['service_type']}</td><td>{l['zip']}</td><td>{l['status']}</td></tr>"
    html += "</table><p><a href='/'>Home</a></p></body></html>"
    return html

@app.route("/buy/<int:lead_id>")
@login_required
def buy(lead_id):
    with get_db() as db:
        lead = db.execute("SELECT * FROM leads WHERE id=? AND status='available'", (lead_id,)).fetchone()
        if lead:
            db.execute("UPDATE leads SET status='sold', assigned_to=?, assigned_at=CURRENT_TIMESTAMP WHERE id=?", (session["contractor_id"], lead_id))
            db.execute("INSERT INTO assignments (lead_id, contractor_id, status) VALUES (?,?,'accepted')", (lead_id, session["contractor_id"]))
            db.commit()
            flash(f"Lead #{lead_id} purchased.")
        else:
            flash("Lead not available.")
    return redirect(url_for("leads"))

@app.route("/privacy")
def privacy():
    return """<html><body style="font-family:Arial;max-width:800px;margin:40px auto;padding:20px;"><h1>Privacy Policy</h1><p>Last updated: October 22, 2026</p><p>We collect contact info to match exclusive leads. Data is shared only with the matched contractor. Subject to Minnesota law.</p><p><a href="/">Home</a></p></body></html>"""

@app.route("/terms")
def terms():
    return """<html><body style="font-family:Arial;max-width:800px;margin:40px auto;padding:20px;"><h1>Terms & Conditions</h1><p>Last updated: October 22, 2026</p><ul><li>Exclusive leads only</li><li>Independent contractors</li><li>Minnesota law governs</li></ul><p><a href="/">Home</a></p></body></html>"""

@app.route("/admin_login", methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("email")==ADMIN_EMAIL and request.form.get("password")==ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(url_for("admin"))
        flash("Invalid credentials.")
    return """<html><body style="font-family:Arial;max-width:500px;margin:40px auto;padding:20px;"><h1>Admin Login</h1><form method="post"><input name="email" type="email" placeholder="Email"><input name="password" type="password" placeholder="Password"><button>Login</button></form></body></html>"""

@app.route("/admin")
@admin_required
def admin():
    with get_db() as db:
        contractors = db.execute("SELECT COUNT(*) c FROM contractors").fetchone()["c"]
        leads = db.execute("SELECT COUNT(*) c FROM leads").fetchone()["c"]
        available = db.execute("SELECT COUNT(*) c FROM leads WHERE status='available'").fetchone()["c"]
    return f"""
    <html><body style="font-family:Arial;max-width:800px;margin:40px auto;padding:20px;">
    <h1>Admin Dashboard</h1>
    <p>Contractors: {contractors} | Leads: {leads} | Available: {available}</p>
    <p><a href="/seed">Seed Demo Data</a> | <a href="/assignments">View Assignments</a> | <a href="/auto_match">Auto-Match</a> | <a href="/admin_logout">Logout</a></p>
    </body></html>
    """

@app.route("/admin_logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("home"))

@app.route("/seed")
@admin_required
def seed():
    services = ["Water Damage","Mold","Roofing","Siding","Windows","Bathroom","Kitchen","Additions","Drywall","Flooring"]
    zips = ["55331","55343","55344","55345","55346","55347","55391","55424","55435","55436","55437","55438","55439"]
    with get_db() as db:
        for i in range(50):
            try:
                db.execute("INSERT INTO contractors (name,email,phone,company,services,license_number,active) VALUES (?,?,?,?,?,?,1)",
                    (f"Contractor {i+1}", f"c{i+1}@demo.com", f"612-555-{1000+i:04d}", f"Co {i+1}",
                     random.choice(services), f"MN-{100000+i}"))
            except: pass
        for i in range(100):
            db.execute("INSERT INTO leads (name,phone,email,zip,service_type,details,status,price) VALUES (?,?,?,?,?,?, 'available', ?)",
                (f"Homeowner {i+1}", f"612-555-{2000+i:04d}", f"h{i+1}@demo.com", random.choice(zips),
                 random.choice(services), "Demo job description", 45.0))
        db.commit()
    return "<p>Seeded 50 contractors and 100 leads. <a href='/admin'>Back</a></p>"

@app.route("/assignments")
@admin_required
def assignments():
    with get_db() as db:
        rows = db.execute("""
            SELECT a.id, l.name lead_name, l.service_type, c.name contractor_name, a.status, a.created
            FROM assignments a
            JOIN leads l ON a.lead_id = l.id
            JOIN contractors c ON a.contractor_id = c.id
            ORDER BY a.created DESC
        """).fetchall()
    html = "<html><body style='font-family:Arial;max-width:900px;margin:40px auto;padding:20px;'><h1>Assignments</h1><table border='1' cellpadding='6'><tr><th>ID</th><th>Lead</th><th>Service</th><th>Contractor</th><th>Status</th><th>When</th></tr>"
    for r in rows:
        html += f"<tr><td>{r['id']}</td><td>{r['lead_name']}</td><td>{r['service_type']}</td><td>{r['contractor_name']}</td><td>{r['status']}</td><td>{r['created']}</td></tr>"
    html += "</table><p><a href='/admin'>Back</a></p></body></html>"
    return html

@app.route("/auto_match")
@admin_required
def auto_match():
    with get_db() as db:
        leads = db.execute("SELECT * FROM leads WHERE status='available'").fetchall()
        matched = 0
        for lead in leads:
            contractor = db.execute("SELECT * FROM contractors WHERE active=1 AND services LIKE ? LIMIT 1", (f"%{lead['service_type']}%",)).fetchone()
            if contractor:
                db.execute("UPDATE leads SET status='assigned', assigned_to=?, assigned_at=CURRENT_TIMESTAMP WHERE id=?", (contractor["id"], lead["id"]))
                db.execute("INSERT INTO assignments (lead_id, contractor_id, status) VALUES (?,?,'pending')", (lead["id"], contractor["id"]))
                matched += 1
        db.commit()
    return f"<p>Auto-matched {matched} leads. <a href='/assignments'>View Assignments</a> | <a href='/admin'>Admin</a></p>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
