from flask import Flask, request, render_template_string, redirect, url_for, session
import sqlite3
from datetime import datetime, timedelta
import os
import hashlib

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key-in-production-2026")
DB = "leads.db"

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
        button { background: #0ea5e9; color: white; border: none; border-radius: 6px; cursor: pointer; }
        .agreement { border: 1px solid #ccc; padding: 15px; margin: 15px 0; background: #f9f9f9; }
      </style>
    </head>
    <body>
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
        <button type="submit">Submit Application</button>
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
        a.buy { background: #0ea5e9; color: white; padding: 8px 16px; text-decoration: none; border-radius: 6px; display: inline-block; margin-top: 8px; }
      </style>
    </head>
    <body>
      <h2>Available Exclusive Leads</h2>
      <p class="expire">Leads expire after 24 hours if not accepted.</p>
      {% if leads %}
        {% for l in leads %}
          <div class="lead">
            <strong>{{ l.service }}</strong> — {{ l.zip_code }}<br>
            Price: ${{ "%.2f"|format(l.price) }}<br>
            <a class="buy" href="/buy/{{ l.id }}">Buy Lead</a>
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
        # Clear old demo data for clean test
        db.execute("DELETE FROM contractors WHERE email LIKE 'demo%@test.com'")
        db.execute("DELETE FROM leads WHERE email LIKE 'home%@test.com'")
        # 5 demo contractors
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
        # 10 demo leads
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
    """

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
