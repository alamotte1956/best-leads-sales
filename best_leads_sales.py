from flask import Flask, request, render_template_string, redirect, url_for, session, flash
import sqlite3
import os
from datetime import datetime, timedelta
import hashlib

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")

DB_PATH = "leads.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS contractors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                password_hash TEXT,
                license_number TEXT,
                services TEXT,
                active INTEGER DEFAULT 0,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                phone TEXT,
                email TEXT,
                zip TEXT,
                service_type TEXT,
                details TEXT,
                price REAL DEFAULT 45.0,
                status TEXT DEFAULT 'available',
                assigned_to INTEGER,
                created_at TEXT,
                expires_at TEXT
            );
        """)

init_db()

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

@app.route("/")
def home():
    return """
    <h1>Best Leads</h1>
    <p>Exclusive Twin Cities Leads — One Contractor Per Job</p>
    <p>No shared leads. Contact info hidden until you accept.</p>
    <a href="/contractor_login">Contractor Login</a> |
    <a href="/contractor_signup">Sign Up</a> |
    <a href="/admin">Admin</a>
    """

@app.route("/contractor_signup", methods=["GET", "POST"])
def contractor_signup():
    if request.method == "POST":
        data = {
            "name": request.form.get("name"),
            "email": request.form.get("email"),
            "phone": request.form.get("phone"),
            "password_hash": hash_pw(request.form.get("password", "demo")),
            "license_number": request.form.get("license"),
            "services": request.form.get("services"),
            "created_at": datetime.utcnow().isoformat()
        }
        with get_db() as db:
            try:
                db.execute("""INSERT INTO contractors (name, email, phone, password_hash, license_number, services, created_at)
                              VALUES (:name, :email, :phone, :password_hash, :license_number, :services, :created_at)""", data)
                return "Signup received. Awaiting approval. <a href='/'>Home</a>"
            except sqlite3.IntegrityError:
                return "Email already registered."
    return """
    <h2>Contractor Signup</h2>
    <form method="post">
      Name: <input name="name" required><br>
      Email: <input name="email" type="email" required><br>
      Phone: <input name="phone"><br>
      Password: <input name="password" type="password" required><br>
      MN License #: <input name="license"><br>
      Services: <input name="services" placeholder="Roofing, Water Damage, etc."><br>
      <button type="submit">Apply</button>
    </form>
    <a href="/">Home</a>
    """

@app.route("/contractor_login", methods=["GET", "POST"])
def contractor_login():
    if request.method == "POST":
        email = request.form.get("email")
        pw = hash_pw(request.form.get("password", ""))
        with get_db() as db:
            c = db.execute("SELECT * FROM contractors WHERE email=? AND password_hash=? AND active=1", (email, pw)).fetchone()
            if c:
                session["contractor_id"] = c["id"]
                return redirect("/available_leads")
        return "Invalid login or not yet approved."
    return """
    <h2>Contractor Login</h2>
    <form method="post">
      Email: <input name="email"><br>
      Password: <input name="password" type="password"><br>
      <button>Login</button>
    </form>
    """

@app.route("/available_leads")
def available_leads():
    if "contractor_id" not in session:
        return redirect("/contractor_login")
    with get_db() as db:
        leads = db.execute("SELECT * FROM leads WHERE status='available'").fetchall()
    html = "<h2>Available Exclusive Leads</h2><p style='color:red'>Leads expire after 24 hours if not accepted.</p><ul>"
    for l in leads:
        html += f"<li>{l['service_type']} in {l['zip']} — ${l['price']} <a href='/accept/{l['id']}'>Accept</a></li>"
    html += "</ul><a href='/'>Home</a>"
    return html

@app.route("/accept/<int:lead_id>")
def accept(lead_id):
    if "contractor_id" not in session:
        return redirect("/contractor_login")
    with get_db() as db:
        db.execute("UPDATE leads SET status='accepted', assigned_to=? WHERE id=? AND status='available'",
                   (session["contractor_id"], lead_id))
    return "Lead accepted. Contact info will be shown in your dashboard. <a href='/available_leads'>Back</a>"

@app.route("/admin")
def admin():
    with get_db() as db:
        contractors = db.execute("SELECT * FROM contractors").fetchall()
        leads = db.execute("SELECT * FROM leads").fetchall()
    html = "<h2>Admin</h2><h3>Contractors</h3><ul>"
    for c in contractors:
        html += f"<li>{c['name']} ({c['email']}) — Active: {c['active']} <a href='/toggle/{c['id']}'>Toggle</a></li>"
    html += "</ul><h3>Leads</h3><ul>"
    for l in leads:
        html += f"<li>{l['name']} - {l['service_type']} - {l['status']}</li>"
    html += "</ul><a href='/seed'>Seed Demo</a>"
    return html

@app.route("/toggle/<int:cid>")
def toggle(cid):
    with get_db() as db:
        db.execute("UPDATE contractors SET active = 1 - active WHERE id=?", (cid,))
    return redirect("/admin")

@app.route("/seed")
def seed():
    with get_db() as db:
        for i in range(5):
            db.execute("""INSERT OR IGNORE INTO contractors (name, email, phone, password_hash, license_number, services, active, created_at)
                          VALUES (?,?,?,?,?,?,1,?)""",
                       (f"Demo Contractor {i}", f"demo{i}@example.com", "612-555-0000", hash_pw("demo"), f"LIC{i}", "All", datetime.utcnow().isoformat()))
        for i in range(10):
            db.execute("""INSERT INTO leads (name, phone, email, zip, service_type, details, price, created_at, expires_at)
                          VALUES (?,?,?,?,?,?,45,?,?)""",
                       (f"Lead {i}", "612-555-1111", f"lead{i}@example.com", "55406", "Roofing", "Demo lead",
                        datetime.utcnow().isoformat(), (datetime.utcnow() + timedelta(hours=24)).isoformat()))
    return "Seeded. <a href='/admin'>Admin</a>"

@app.route("/privacy")
def privacy():
    return "<h1>Privacy Policy</h1><p>Contractor and lead data used only for exclusive matching. No shared leads.</p>"

@app.route("/terms")
def terms():
    return "<h1>Terms</h1><p>Exclusive leads only. Subject to Minnesota law. Albert R LaMotte dba Restoration Contractors MN.</p>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
