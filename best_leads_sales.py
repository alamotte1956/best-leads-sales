from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production-please")

# Database setup
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
                name TEXT,
                email TEXT UNIQUE,
                phone TEXT,
                company TEXT,
                services TEXT,
                license_number TEXT,
                insurance TEXT,
                active INTEGER DEFAULT 1,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                phone TEXT,
                email TEXT,
                zip TEXT,
                service_type TEXT,
                details TEXT,
                status TEXT DEFAULT 'available',
                assigned_to INTEGER,
                price REAL DEFAULT 50.0,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(assigned_to) REFERENCES contractors(id)
            );
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER,
                contractor_id INTEGER,
                status TEXT DEFAULT 'pending',
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

init_db()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "contractor_id" not in session:
            return redirect(url_for("contractor_login"))
        return f(*args, **kwargs)
    return decorated

# Routes
@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Best Leads Sales</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }
        a { display: inline-block; margin: 10px; padding: 12px 20px; background: #0ea5e9; color: white; text-decoration: none; border-radius: 6px; }
        a:hover { background: #0284c7; }
    </style>
    </head>
    <body>
        <h1>Best Leads Sales to Contractors</h1>
        <p>Exclusive leads for Twin Cities contractors. No shared leads.</p>
        <a href="/signup">Contractor Signup</a>
        <a href="/contractor_login">Contractor Login</a>
        <a href="/leads">Available Leads</a>
        <a href="/admin">Admin Dashboard</a>
        <a href="/privacy">Privacy Policy</a>
        <a href="/terms">Terms & Conditions</a>
    </body>
    </html>
    """

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        company = request.form.get("company")
        services = request.form.get("services")
        license_number = request.form.get("license_number")
        insurance = request.form.get("insurance")
        with get_db() as db:
            try:
                db.execute(
                    "INSERT INTO contractors (name, email, phone, company, services, license_number, insurance) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (name, email, phone, company, services, license_number, insurance)
                )
                db.commit()
                flash("Signup successful. You can now log in.")
                return redirect(url_for("contractor_login"))
            except sqlite3.IntegrityError:
                flash("Email already registered.")
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Contractor Signup</title>
    <style>body{font-family:Arial;max-width:600px;margin:40px auto;padding:20px;} input,textarea{width:100%;padding:10px;margin:8px 0;border:1px solid #ccc;border-radius:4px;} button{background:#0ea5e9;color:white;padding:12px 24px;border:none;border-radius:6px;cursor:pointer;}</style>
    </head>
    <body>
        <h1>Contractor Signup</h1>
        <form method="post">
            <input name="name" placeholder="Full Name" required><br>
            <input name="email" type="email" placeholder="Email" required><br>
            <input name="phone" placeholder="Phone" required><br>
            <input name="company" placeholder="Company Name"><br>
            <textarea name="services" placeholder="Services offered (e.g. water damage, mold, roofing)"></textarea><br>
            <input name="license_number" placeholder="License Number"><br>
            <input name="insurance" placeholder="Insurance info"><br>
            <button type="submit">Sign Up</button>
        </form>
        <p><a href="/">Back to Home</a></p>
    </body>
    </html>
    """

@app.route("/contractor_login", methods=["GET", "POST"])
def contractor_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        # Auto-admin: if this is the admin email, grant admin session too
        if email == ADMIN_EMAIL:
            session["is_admin"] = True
        with get_db() as db:
            contractor = db.execute("SELECT * FROM contractors WHERE email = ?", (email,)).fetchone()
            if contractor and contractor["active"]:
                session["contractor_id"] = contractor["id"]
                session["contractor_name"] = contractor["name"]
                return redirect(url_for("leads"))
            # Even if not a contractor, if they are admin, let them in
            if email == ADMIN_EMAIL:
                session["contractor_name"] = "Admin"
                return redirect(url_for("admin"))
            flash("Invalid login or inactive account.")
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Contractor Login</title>
    <style>body{font-family:Arial;max-width:500px;margin:40px auto;padding:20px;} input{width:100%;padding:10px;margin:8px 0;border:1px solid #ccc;border-radius:4px;} button{background:#0ea5e9;color:white;padding:12px 24px;border:none;border-radius:6px;}</style>
    </head>
    <body>
        <h1>Contractor Login</h1>
        <form method="post">
            <input name="email" type="email" placeholder="Email" required><br>
            <button type="submit">Login</button>
        </form>
        <p><a href="/signup">Need an account? Sign up</a> | <a href="/">Home</a></p>
    </body>
    </html>
    """


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/leads")
@login_required
def leads():
    with get_db() as db:
        available = db.execute("SELECT * FROM leads WHERE status = 'available' ORDER BY created DESC").fetchall()
        my_leads = db.execute("SELECT * FROM leads WHERE assigned_to = ? ORDER BY created DESC", (session["contractor_id"],)).fetchall()
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Available Leads</title>
    <style>body{{font-family:Arial;max-width:900px;margin:40px auto;padding:20px;}} table{{width:100%;border-collapse:collapse;}} th,td{{border:1px solid #ddd;padding:8px;text-align:left;}} .btn{{background:#0ea5e9;color:white;padding:6px 12px;text-decoration:none;border-radius:4px;}}</style>
    </head>
    <body>
        <h1>Available Exclusive Leads</h1>
        <p>Welcome, {session.get('contractor_name', 'Contractor')} | <a href="/logout">Logout</a></p>
        <h2>Available Leads</h2>
        <table>
            <tr><th>ID</th><th>Service</th><th>ZIP</th><th>Price</th><th>Action</th></tr>
    """
    for lead in available:
        html += f"<tr><td>{lead['id']}</td><td>{lead['service_type']}</td><td>{lead['zip']}</td><td>${lead['price']}</td><td><a class='btn' href='/buy/{lead['id']}'>Buy Exclusive Lead</a></td></tr>"
    html += "</table><h2>My Assigned Leads</h2><table><tr><th>ID</th><th>Service</th><th>ZIP</th><th>Status</th></tr>"
    for lead in my_leads:
        html += f"<tr><td>{lead['id']}</td><td>{lead['service_type']}</td><td>{lead['zip']}</td><td>{lead['status']}</td></tr>"
    html += "</table><p><a href='/'>Home</a></p></body></html>"
    return html

@app.route("/buy/<int:lead_id>")
@login_required
def buy_lead(lead_id):
    with get_db() as db:
        lead = db.execute("SELECT * FROM leads WHERE id = ? AND status = 'available'", (lead_id,)).fetchone()
        if lead:
            db.execute("UPDATE leads SET status = 'sold', assigned_to = ? WHERE id = ?", (session["contractor_id"], lead_id))
            db.execute("INSERT INTO assignments (lead_id, contractor_id, status) VALUES (?, ?, 'accepted')", (lead_id, session["contractor_id"]))
            db.commit()
            flash(f"Lead #{lead_id} purchased successfully! Contact info is now available.")
        else:
            flash("Lead not available.")
    return redirect(url_for("leads"))

@app.route("/privacy")
def privacy():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Privacy Policy</title>
    <style>body{font-family:Arial;max-width:800px;margin:40px auto;padding:20px;line-height:1.6;}</style>
    </head>
    <body>
        <h1>Privacy Policy</h1>
        <p><strong>Last updated:</strong> October 22, 2026</p>
        <p>This site collects contact information (name, phone, email, address) from homeowners and contractors for the purpose of connecting exclusive leads with independent contractors in the Twin Cities area.</p>
        <p>We do not sell or share personal data with third parties beyond the specific contractor who purchases an exclusive lead.</p>
        <p>SMS notifications are optional. By providing your phone number and checking the consent box, you agree to receive transactional messages. You may opt out at any time by replying STOP.</p>
        <p>Data is stored securely and retained only as long as necessary for the service.</p>
        <p>Subject to Minnesota law.</p>
        <p><a href="/">Back to Home</a></p>
    </body>
    </html>
    """

@app.route("/terms")
def terms():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Terms & Conditions</title>
    <style>body{font-family:Arial;max-width:800px;margin:40px auto;padding:20px;line-height:1.6;}</style>
    </head>
    <body>
        <h1>Terms & Conditions</h1>
        <p><strong>Last updated:</strong> October 22, 2026</p>
        <p>By using this platform you agree to the following:</p>
        <ul>
            <li>Leads are exclusive — only one contractor receives the homeowner contact information.</li>
            <li>Contractors are independent and responsible for their own licensing, insurance, and work quality.</li>
            <li>Homeowners understand they are connecting with independent contractors, not employees of this platform.</li>
            <li>Payment for leads is due upon purchase. Refunds are not available once contact information is revealed.</li>
            <li>All parties agree that Minnesota law governs this agreement.</li>
        </ul>
        <p>This platform acts solely as a lead marketplace and is not responsible for the work performed by contractors.</p>
        <p><a href="/">Back to Home</a></p>
    </body>
    </html>
    """

# Admin credentials (change in production)
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "alamotte1956@gmail.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "PeggySmith1$")

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(url_for("admin"))
        flash("Invalid admin credentials.")
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Admin Login</title>
    <style>body{font-family:Arial;max-width:500px;margin:40px auto;padding:20px;} input{width:100%;padding:10px;margin:8px 0;border:1px solid #ccc;border-radius:4px;} button{background:#0ea5e9;color:white;padding:12px 24px;border:none;border-radius:6px;}</style>
    </head>
    <body>
        <h1>Admin Login</h1>
        <form method="post">
            <input name="email" type="email" placeholder="Admin Email" required><br>
            <input name="password" type="password" placeholder="Password" required><br>
            <button type="submit">Login</button>
        </form>
        <p><a href="/">Home</a></p>
    </body>
    </html>
    """

@app.route("/admin_logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("home"))

@app.route("/admin")
@admin_required
def admin():
    with get_db() as db:
        contractors = db.execute("SELECT * FROM contractors ORDER BY created DESC").fetchall()
        leads = db.execute("SELECT * FROM leads ORDER BY created DESC").fetchall()
        # Simple assignment view (leads that have been assigned)
        assigned = db.execute("""
            SELECT l.id, l.name as lead_name, l.service_type, l.zip, l.status, l.price,
                   c.name as contractor_name, c.email as contractor_email
            FROM leads l
            LEFT JOIN contractors c ON l.assigned_to = c.id
            WHERE l.assigned_to IS NOT NULL
            ORDER BY l.created DESC
        """).fetchall()
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Admin Dashboard</title>
    <style>
        body{font-family:Arial;max-width:1100px;margin:40px auto;padding:20px;}
        table{width:100%;border-collapse:collapse;margin:20px 0;}
        th,td{border:1px solid #ddd;padding:8px;text-align:left;}
        .btn{background:#0ea5e9;color:white;padding:10px 16px;border:none;border-radius:6px;text-decoration:none;display:inline-block;margin:8px 4px;}
    </style>
    </head>
    <body>
        <h1>Admin Dashboard</h1>
        <p>
            <a class="btn" href="/auto_match">Run Auto-Match</a>
            <a class="btn" href="/assignments">View Assignments</a>
            <a href="/admin_logout">Logout</a>
        </p>
        <h2>Contractors</h2>
        <table><tr><th>ID</th><th>Name</th><th>Email</th><th>Phone</th><th>Active</th></tr>
    """
    for c in contractors:
        html += f"<tr><td>{c['id']}</td><td>{c['name']}</td><td>{c['email']}</td><td>{c['phone']}</td><td>{'Yes' if c['active'] else 'No'}</td></tr>"
    html += "</table><h2>Leads</h2><table><tr><th>ID</th><th>Name</th><th>Service</th><th>ZIP</th><th>Status</th><th>Price</th></tr>"
    for l in leads:
        html += f"<tr><td>{l['id']}</td><td>{l['name']}</td><td>{l['service_type']}</td><td>{l['zip']}</td><td>{l['status']}</td><td>${l['price']}</td></tr>"
    html += "</table></body></html>"
    return html

@app.route("/assignments")
@admin_required
def assignments():
    with get_db() as db:
        rows = db.execute("""
            SELECT l.id, l.name as lead_name, l.phone as lead_phone, l.service_type, l.zip, l.status,
                   c.name as contractor_name, c.email as contractor_email, c.phone as contractor_phone
            FROM leads l
            LEFT JOIN contractors c ON l.assigned_to = c.id
            WHERE l.assigned_to IS NOT NULL
            ORDER BY l.created DESC
        """).fetchall()
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Assignments</title>
    <style>body{font-family:Arial;max-width:1000px;margin:40px auto;padding:20px;} table{width:100%;border-collapse:collapse;} th,td{border:1px solid #ddd;padding:8px;}</style>
    </head>
    <body>
        <h1>Contractor ↔ Consumer Assignments</h1>
        <p><a href="/admin">Back to Admin</a> | <a href="/auto_match">Run Auto-Match</a></p>
        <table>
            <tr><th>Lead ID</th><th>Consumer</th><th>Service</th><th>ZIP</th><th>Contractor</th><th>Contractor Email</th><th>Status</th></tr>
    """
    for r in rows:
        html += f"<tr><td>{r['id']}</td><td>{r['lead_name']}<br><small>{r['lead_phone']}</small></td><td>{r['service_type']}</td><td>{r['zip']}</td><td>{r['contractor_name'] or '—'}</td><td>{r['contractor_email'] or '—'}</td><td>{r['status']}</td></tr>"
    if not rows:
        html += "<tr><td colspan='7'>No assignments yet. Run Auto-Match.</td></tr>"
    html += "</table></body></html>"
    return html

@app.route("/auto_match")
@admin_required
def auto_match():
    with get_db() as db:
        # Simple auto-match: assign each unassigned lead to an active contractor (round-robin style)
        unassigned = db.execute("SELECT * FROM leads WHERE assigned_to IS NULL OR assigned_to = ''").fetchall()
        contractors = db.execute("SELECT * FROM contractors WHERE active = 1").fetchall()
        if not contractors:
            return "<h2>No active contractors.</h2><p><a href='/admin'>Back</a></p>"
        for i, lead in enumerate(unassigned):
            contractor = contractors[i % len(contractors)]
            db.execute("UPDATE leads SET assigned_to = ?, status = 'assigned' WHERE id = ?", (contractor["id"], lead["id"]))
        db.commit()
    return redirect(url_for("assignments"))


# Demo seed route (optional)
@app.route("/seed")
def seed():
    with get_db() as db:
        # Add a few demo contractors and leads if empty
        count = db.execute("SELECT COUNT(*) FROM contractors").fetchone()[0]
        if count == 0:
            db.execute("INSERT INTO contractors (name, email, phone, company, services) VALUES (?, ?, ?, ?, ?)",
                       ("Demo Contractor", "demo@contractor.com", "612-555-0100", "Demo Restoration", "water damage, mold"))
            db.execute("INSERT INTO leads (name, phone, email, zip, service_type, details, price) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       ("Jane Homeowner", "612-555-0200", "jane@example.com", "55406", "Water Damage", "Basement flooding", 75.0))
            db.commit()
    return redirect(url_for("admin"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
