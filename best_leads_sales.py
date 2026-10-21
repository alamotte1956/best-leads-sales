from flask import Flask, request, render_template_string, redirect, url_for, session
import sqlite3
from datetime import datetime, timedelta
import os
import hashlib

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key-in-production-2026")
DB = "leads.db"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS contractors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT UNIQUE,
            license_number TEXT,
            years_in_business INTEGER,
            services TEXT,
            password_hash TEXT,
            active INTEGER DEFAULT 1,
            created TEXT
        );
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            email TEXT,
            zip_code TEXT,
            service TEXT,
            details TEXT,
            price REAL DEFAULT 75.0,
            status TEXT DEFAULT 'available',
            assigned_to INTEGER,
            created TEXT,
            expires TEXT
        );
        """)
        db.commit()

init_db()

def hash_pw(pw):
    if not pw:
        pw = "demo123"
    return hashlib.sha256(pw.encode()).hexdigest()

def is_admin():
    return session.get("is_admin") is True

CONTRACTOR_AGREEMENT = """
By signing up you agree:
- You hold a valid Minnesota contractor license
- You receive exclusive leads only (one contractor per job)
- You are responsible for your own liability insurance and workers’ compensation
- Restoration Contractors MN verifies your Minnesota license only — not insurance
- All agreements are subject to Minnesota law
"""

@app.route("/")
def home():
    return redirect(url_for("available"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        d = request.form
        if not d.get("agree"):
            return "You must agree to the terms.", 400
        pw = hash_pw(d.get("password"))
        try:
            with get_db() as db:
                db.execute("""
                    INSERT INTO contractors (name, phone, email, license_number, years_in_business, services, password_hash, created)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    d.get("name", ""),
                    d.get("phone", ""),
                    d.get("email", ""),
                    d.get("license_number", ""),
                    int(d.get("years") or 0),
                    d.get("services", ""),
                    pw,
                    datetime.now().isoformat()
                ))
                db.commit()
            return "<h2>Application received. We will review your Minnesota license.</h2><p><a href='/contractor_login'>Login here</a></p>"
        except sqlite3.IntegrityError:
            return "Email already registered. Try logging in.", 400
        except Exception as e:
            return f"Error: {str(e)}", 500
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Contractor Signup - Restoration Contractors MN</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        body { font-family: system-ui, sans-serif; max-width: 600px; margin: 40px auto; padding: 20px; }
        input, button { width: 100%; padding: 12px; margin: 8px 0; box-sizing: border-box; }
        button { background: #0ea5e9; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 16px; }
        .agreement { border: 1px solid #ccc; padding: 15px; margin: 15px 0; background: #f9f9f9; }
        .cta-box { background: #f0f9ff; border: 1px solid #bae6fd; padding: 16px; border-radius: 10px; margin-bottom: 20px; }
      </style>
    </head>
    <body>
      <div class="cta-box">
        <h3>Get Exclusive Twin Cities Leads</h3>
        <p>Stop competing with 3–5 other contractors on every job. Sign up for exclusive leads only — one contractor per homeowner.</p>
        <p><strong>Competitive pricing. Higher close rates. No shared leads.</strong></p>
      </div>
      <h2>Contractor Signup</h2>
      <form method="post">
        <input name="name" placeholder="Business Name" required>
        <input name="phone" placeholder="Phone" required>
        <input name="email" type="email" placeholder="Email" required>
        <input name="license_number" placeholder="MN License Number" required>
        <input name="years" type="number" placeholder="Years in business" min="0">
        <input name="services" placeholder="Services (roofing, water damage, etc.)">
        <input name="password" type="password" placeholder="Password" required>
        <div class="agreement">
          <strong>Contractor Agreement</strong><br>
          {{ agreement }}
          <label style="display:block; margin-top:10px;">
            <input type="checkbox" name="agree" required> I agree to the Contractor Agreement
          </label>
        </div>
        <button type="submit">Start Getting Exclusive Leads</button>
      </form>
    </body>
    </html>
    """, agreement=CONTRACTOR_AGREEMENT)

@app.route("/contractor_login", methods=["GET", "POST"])
def contractor_login():
    if request.method == "POST":
        email = request.form.get("email", "")
        pw = hash_pw(request.form.get("password", ""))
        with get_db() as db:
            c = db.execute("SELECT * FROM contractors WHERE email=? AND password_hash=?", (email, pw)).fetchone()
        if c:
            session["contractor_id"] = c["id"]
            session["contractor_name"] = c["name"]
            return redirect(url_for("contractor_profile"))
        return "<p>Invalid email or password.</p><a href='/contractor_login'>Try again</a>"
    return """
    <!DOCTYPE html>
    <html>
    <head>
      <title>Contractor Login</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        body { font-family: system-ui, sans-serif; max-width: 400px; margin: 60px auto; padding: 20px; }
        input, button { width: 100%; padding: 12px; margin: 8px 0; box-sizing: border-box; }
        button { background: #0ea5e9; color: white; border: none; border-radius: 6px; }
      </style>
    </head>
    <body>
      <h2>Contractor Login</h2>
      <form method="post">
        <input name="email" type="email" placeholder="Email" required>
        <input name="password" type="password" placeholder="Password" required>
        <button type="submit">Login</button>
      </form>
    </body>
    </html>
    """

@app.route("/contractor_profile")
def contractor_profile():
    cid = session.get("contractor_id")
    if not cid:
        return redirect(url_for("contractor_login"))
    with get_db() as db:
        c = db.execute("SELECT * FROM contractors WHERE id=?", (cid,)).fetchone()
        leads = db.execute("SELECT * FROM leads WHERE assigned_to=? AND status='sold' ORDER BY created DESC", (cid,)).fetchall()
    if not c:
        session.clear()
        return redirect(url_for("contractor_login"))
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Your Profile</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        body { font-family: system-ui, sans-serif; max-width: 700px; margin: 40px auto; padding: 20px; }
        .lead { border: 1px solid #ddd; padding: 12px; margin: 10px 0; border-radius: 6px; }
        a { color: #0ea5e9; }
      </style>
    </head>
    <body>
      <h2>{{ c.name }} — Your Leads</h2>
      <p><strong>License:</strong> {{ c.license_number or 'Not provided' }}</p>
      <p><strong>Email:</strong> {{ c.email }}</p>
      <p><a href="/available">Available Leads</a> | <a href="/logout">Logout</a></p>
      <h3>Purchased Leads</h3>
      {% if leads %}
        {% for l in leads %}
          <div class="lead">
            <strong>{{ l.service }}</strong> in {{ l.zip_code }}<br>
            Price: ${{ "%.2f"|format(l.price) }}<br>
            Contact: {{ l.name }} — {{ l.phone }}
          </div>
        {% endfor %}
      {% else %}
        <p>No purchased leads yet.</p>
      {% endif %}
    </body>
    </html>
    """, c=c, leads=leads)

@app.route("/available")
def available():
    now = datetime.now().isoformat()
    with get_db() as db:
        leads = db.execute(
            "SELECT * FROM leads WHERE status='available' AND expires > ? ORDER BY created DESC",
            (now,)
        ).fetchall()
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Available Exclusive Leads</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        body { font-family: system-ui, sans-serif; max-width: 700px; margin: 40px auto; padding: 20px; }
        .lead { border: 1px solid #ddd; padding: 15px; margin: 12px 0; border-radius: 8px; }
        .expire { color: #dc2626; font-weight: bold; }
        a.buy { background: #0ea5e9; color: white; padding: 10px 18px; text-decoration: none; border-radius: 6px; display: inline-block; margin-top: 8px; font-weight: 600; }
        .cta-box { background: #f0f9ff; border: 1px solid #bae6fd; padding: 16px; border-radius: 10px; margin-bottom: 20px; }
        .cta-box h3 { margin-top: 0; color: #0369a1; }
        .guarantee { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 16px; border-radius: 10px; margin: 20px 0; }
        .guarantee h3 { margin-top: 0; color: #166534; }
        .guarantee ul { margin: 8px 0 0 20px; }
      </style>
    </head>
    <body>
      <h2>Available Exclusive Leads</h2>
      <div class="cta-box">
        <h3>Get Exclusive Jobs — No Shared Leads</h3>
        <p>These leads go to one contractor only. Buy now before they expire in 24 hours.</p>
        <p><strong>Competitive Twin Cities pricing. Higher close rates.</strong></p>
      </div>
      <div class="guarantee">
        <h3>Lead Quality Guarantees</h3>
        <ul>
          <li><strong>100% Exclusive</strong> — sold to one contractor only. Never shared.</li>
          <li><strong>Contact info hidden</strong> until you purchase the lead.</li>
          <li><strong>24-hour expiration</strong> if not accepted — no stale leads.</li>
          <li><strong>Minnesota licensed contractors only</strong> on the platform.</li>
          <li><strong>Competitive local pricing</strong> based on Twin Cities market rates.</li>
        </ul>
      </div>
      <p class="expire">Leads expire after 24 hours if not accepted.</p>
      {% if leads %}
        {% for l in leads %}
          <div class="lead">
            <strong>{{ l.service }}</strong> — {{ l.zip_code }}<br>
            Price: ${{ "%.2f"|format(l.price) }}<br>
            <a class="buy" href="/buy/{{ l.id }}">Buy This Exclusive Lead</a>
          </div>
        {% endfor %}
      {% else %}
        <p>No available leads right now. Check back soon or <a href="/seed_demo">seed demo data</a>.</p>
      {% endif %}
      <p><a href="/contractor_profile">My Profile</a> | <a href="/logout">Logout</a></p>
    </body>
    </html>
    """, leads=leads)

@app.route("/buy/<int:lead_id>")
def buy(lead_id):
    cid = session.get("contractor_id")
    if not cid:
        return redirect(url_for("contractor_login"))
    with get_db() as db:
        lead = db.execute("SELECT * FROM leads WHERE id=? AND status='available'", (lead_id,)).fetchone()
        if not lead:
            return "Lead not available or already sold.", 400
        db.execute(
            "UPDATE leads SET status='sold', assigned_to=? WHERE id=?",
            (cid, lead_id)
        )
        db.commit()
    return """
    <h2>Lead purchased successfully (demo mode).</h2>
    <p><a href="/contractor_profile">View your leads</a></p>
    <p><a href="/available">Back to available leads</a></p>
    """

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("contractor_login"))

@app.route("/seed_demo")
def seed_demo():
    with get_db() as db:
        db.execute("DELETE FROM contractors WHERE email LIKE 'demo%@test.com'")
        db.execute("DELETE FROM leads WHERE email LIKE 'home%@test.com'")
        for i in range(1, 6):
            db.execute("""
                INSERT OR IGNORE INTO contractors (name, phone, email, license_number, years_in_business, services, password_hash, created)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"Demo Contractor {i}",
                f"612-555-100{i}",
                f"demo{i}@test.com",
                f"MN-{1000+i}",
                5 + i,
                "roofing, water damage, mold",
                hash_pw("demo123"),
                datetime.now().isoformat()
            ))
        services = ["Roofing", "Water Damage", "Mold Remediation", "Bathroom Remodel", "Kitchen Remodel"]
        for i in range(1, 11):
            exp = (datetime.now() + timedelta(hours=24)).isoformat()
            db.execute("""
                INSERT INTO leads (name, phone, email, zip_code, service, details, price, created, expires, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'available')
            """, (
                f"Homeowner {i}",
                f"612-555-200{i}",
                f"home{i}@test.com",
                "55344",
                services[i % len(services)],
                "Need help soon",
                75.0,
                datetime.now().isoformat(),
                exp
            ))
        db.commit()
    return """
    <h2>Demo data seeded successfully.</h2>
    <p><a href="/available">View available leads</a></p>
    <p><a href="/contractor_login">Login as demo1@test.com / demo123</a></p>
    <p><a href="/admin">Admin panel</a></p>
    """

# ---------- ADMIN OVERRIDES ----------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST" and request.form.get("password") == ADMIN_PASSWORD:
        session["is_admin"] = True
        return redirect(url_for("admin"))
    if not is_admin():
        return """
        <h2>Admin Login</h2>
        <form method="post">
          <input type="password" name="password" placeholder="Admin password" required>
          <button type="submit">Login</button>
        </form>
        <p>Default: admin123</p>
        """
    with get_db() as db:
        contractors = db.execute("SELECT * FROM contractors ORDER BY id DESC").fetchall()
        leads = db.execute("SELECT * FROM leads ORDER BY id DESC").fetchall()
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Admin Overrides</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        body { font-family: system-ui, sans-serif; max-width: 900px; margin: 30px auto; padding: 15px; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        button, input[type=submit] { background: #0ea5e9; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; }
        .section { margin: 30px 0; }
        a { color: #0ea5e9; }
      </style>
    </head>
    <body>
      <h1>Admin Overrides</h1>
      <p><a href="/available">Available Leads</a> | <a href="/logout">Logout</a></p>

      <div class="section">
        <h2>Contractors — Turn On/Off</h2>
        <table>
          <tr><th>ID</th><th>Name</th><th>License</th><th>Active</th><th>Action</th></tr>
          {% for c in contractors %}
          <tr>
            <td>{{ c.id }}</td>
            <td>{{ c.name }}</td>
            <td>{{ c.license_number }}</td>
            <td>{{ "Yes" if c.active else "No" }}</td>
            <td>
              <form method="post" action="/admin/toggle/{{ c.id }}" style="display:inline;">
                <button type="submit">{{ "Deactivate" if c.active else "Activate" }}</button>
              </form>
            </td>
          </tr>
          {% endfor %}
        </table>
      </div>

      <div class="section">
        <h2>Leads — Change Price or Assign</h2>
        <table>
          <tr><th>ID</th><th>Service</th><th>ZIP</th><th>Price</th><th>Status</th><th>Assigned</th><th>Actions</th></tr>
          {% for l in leads %}
          <tr>
            <td>{{ l.id }}</td>
            <td>{{ l.service }}</td>
            <td>{{ l.zip_code }}</td>
            <td>${{ "%.2f"|format(l.price) }}</td>
            <td>{{ l.status }}</td>
            <td>{{ l.assigned_to or "-" }}</td>
            <td>
              <form method="post" action="/admin/price/{{ l.id }}" style="display:inline;">
                <input type="number" name="price" value="{{ l.price }}" step="0.01" style="width:80px;">
                <button type="submit">Update Price</button>
              </form>
              <form method="post" action="/admin/assign/{{ l.id }}" style="display:inline; margin-left:10px;">
                <input type="number" name="contractor_id" placeholder="Contractor ID" style="width:100px;">
                <button type="submit">Assign</button>
              </form>
            </td>
          </tr>
          {% endfor %}
        </table>
      </div>
    </body>
    </html>
    """, contractors=contractors, leads=leads)

@app.route("/admin/toggle/<int:cid>", methods=["POST"])
def admin_toggle(cid):
    if not is_admin():
        return redirect(url_for("admin"))
    with get_db() as db:
        db.execute("UPDATE contractors SET active = CASE WHEN active=1 THEN 0 ELSE 1 END WHERE id=?", (cid,))
        db.commit()
    return redirect(url_for("admin"))

@app.route("/admin/price/<int:lid>", methods=["POST"])
def admin_price(lid):
    if not is_admin():
        return redirect(url_for("admin"))
    try:
        new_price = float(request.form.get("price", 75))
        with get_db() as db:
            db.execute("UPDATE leads SET price=? WHERE id=?", (new_price, lid))
            db.commit()
    except:
        pass
    return redirect(url_for("admin"))

@app.route("/admin/assign/<int:lid>", methods=["POST"])
def admin_assign(lid):
    if not is_admin():
        return redirect(url_for("admin"))
    try:
        cid = int(request.form.get("contractor_id", 0))
        with get_db() as db:
            db.execute("UPDATE leads SET assigned_to=?, status='sold' WHERE id=?", (cid, lid))
            db.commit()
    except:
        pass
    return redirect(url_for("admin"))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
