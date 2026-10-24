from flask import Flask, request, session, redirect, url_for, render_template_string, flash
import sqlite3
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")
DB_PATH = "sales.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS contractors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT,
                contact TEXT,
                phone TEXT,
                email TEXT,
                services TEXT,
                active INTEGER DEFAULT 1,
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
                price REAL DEFAULT 0,
                status TEXT DEFAULT 'available',
                assigned_to INTEGER,
                created_at TEXT,
                expires_at TEXT
            );
        """)

init_db()

STYLE = """
<style>
:root { --primary:#0ea5e9; --dark:#0f172a; --muted:#64748b; --bg:#f8fafc; --card:#ffffff; --red:#dc2626; }
* { box-sizing:border-box; }
body { margin:0; font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; background:var(--bg); color:#1e293b; line-height:1.6; }
.container { max-width:960px; margin:32px auto; padding:0 20px; }
.card { background:var(--card); border-radius:16px; padding:32px; margin:20px 0; box-shadow:0 10px 40px rgba(0,0,0,.08); }
h1,h2 { margin-top:0; color:var(--dark); }
.badge { display:inline-block; background:#dbeafe; color:#1e40af; padding:6px 14px; border-radius:999px; font-size:.85rem; font-weight:600; margin-bottom:12px; }
.nav { margin:24px 0; display:flex; flex-wrap:wrap; gap:18px; }
.nav a { color:var(--primary); text-decoration:none; font-weight:600; }
.nav a:hover { text-decoration:underline; }
.red { color:var(--red); font-weight:700; }
input,select,textarea { width:100%; padding:12px 14px; margin:8px 0 16px; border:1.5px solid #cbd5e1; border-radius:8px; font-size:16px; }
input:focus,select:focus,textarea:focus { outline:none; border-color:var(--primary); }
button, .btn { background:var(--primary); color:#fff; border:none; padding:14px 28px; border-radius:8px; cursor:pointer; font-weight:600; font-size:16px; text-decoration:none; display:inline-block; }
button:hover, .btn:hover { background:#0284c7; }
.btn-secondary { background:#64748b; }
.lead-card { border-left:4px solid var(--primary); }
.inactive { opacity:.6; }
footer { text-align:center; padding:48px 20px; color:var(--muted); font-size:.9rem; }
@media (max-width:640px) { .card { padding:24px 16px; } .nav { flex-direction:column; } }
</style>
"""

def is_expired(lead):
    if not lead["expires_at"]:
        return False
    try:
        return datetime.fromisoformat(lead["expires_at"]) < datetime.utcnow()
    except Exception:
        return False

@app.route("/")
def home():
    return render_template_string(f"""
    {STYLE}
    <div class="container">
      <div class="card">
        <div class="badge">EXCLUSIVE LEADS ONLY · NO SHARED LEADS</div>
        <h1>Best Leads</h1>
        <p>Premium exclusive Twin Cities contractor leads. One contractor per job. Contact information remains hidden until you accept.</p>
        <p class="red">Leads expire after 24 hours if not accepted.</p>
        <div class="nav">
          <a href="/available_leads">Available Leads</a>
          <a href="/signup">Sign Up</a>
          <a href="/contractor_login">Login</a>
          <a href="/contractors">Manage Contractors</a>
          <a href="/privacy">Privacy</a>
          <a href="/terms">Terms</a>
        </div>
      </div>
    </div>
    <footer>Albert R LaMotte dba Restoration Contractors MN · Exclusive matching · Minnesota law applies</footer>
    """)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        d = request.form.to_dict()
        d["created_at"] = datetime.utcnow().isoformat()
        with get_db() as db:
            db.execute("""
                INSERT INTO contractors (company, contact, phone, email, services, created_at)
                VALUES (:company, :contact, :phone, :email, :services, :created_at)
            """, d)
        return render_template_string(f"""{STYLE}<div class="container"><div class="card"><h2>Application Received</h2><p>Thank you. We will review and activate your account for exclusive leads.</p><a href="/" class="btn">Return Home</a></div></div>""")
    return render_template_string(f"""
    {STYLE}
    <div class="container">
      <div class="card">
        <h2>Contractor Sign Up</h2>
        <p>Apply for exclusive Twin Cities leads. No shared leads.</p>
        <form method="post">
          <label>Company Name</label><input name="company" required>
          <label>Contact Person</label><input name="contact" required>
          <label>Phone</label><input name="phone" required>
          <label>Email</label><input name="email" type="email" required>
          <label>Services Offered</label><input name="services" required placeholder="Roofing, Water Damage, Remodeling, etc.">
          <p style="font-size:.9rem;color:#64748b;">By submitting you agree to the terms of Restoration Contractors MN (Albert R LaMotte dba). Exclusive leads only. Subject to Minnesota law, including the Home Solicitation Sales Act.</p>
          <button type="submit">Submit Application</button>
        </form>
        <p><a href="/">← Home</a></p>
      </div>
    </div>
    """)

@app.route("/available_leads")
def available_leads():
    with get_db() as db:
        rows = db.execute("SELECT * FROM leads WHERE status='available' ORDER BY created_at DESC").fetchall()
    cards = ""
    if not rows:
        cards = '<div class="card"><p>No exclusive leads available right now.</p></div>'
    else:
        for r in rows:
            expired = is_expired(r)
            price = r["price"] or 0
            status_note = "<span class='red'>EXPIRED</span>" if expired else "Available"
            cards += f'''
            <div class="card lead-card">
              <strong>{r["service_type"]}</strong> • ZIP {r["zip"]}<br>
              Price: ${price:.0f} · Status: {status_note}<br>
              <em>Contact information hidden until accepted.</em><br>
              <small style="color:#64748b;">Posted: {r["created_at"]}</small>
              {"<form method='post' action='/accept_lead' style='margin-top:12px'><input type='hidden' name='lead_id' value='" + str(r["id"]) + "'><button type='submit'>Accept Lead</button></form>" if not expired else ""}
            </div>
            '''
    return render_template_string(f"""
    {STYLE}
    <div class="container">
      <div class="card">
        <h2>Available Exclusive Leads</h2>
        <p>Contact info is completely hidden until you accept the lead.</p>
        <p class="red">Leads expire after 24 hours if not accepted.</p>
        <p><a href="/">← Home</a></p>
      </div>
      {cards}
    </div>
    """)

@app.route("/accept_lead", methods=["POST"])
def accept_lead():
    lead_id = request.form.get("lead_id")
    if lead_id:
        with get_db() as db:
            db.execute("UPDATE leads SET status='accepted' WHERE id=? AND status='available'", (lead_id,))
    return redirect(url_for("available_leads"))

@app.route("/contractors")
def contractors():
    with get_db() as db:
        rows = db.execute("SELECT * FROM contractors ORDER BY created_at DESC").fetchall()
    cards = ""
    for r in rows:
        status = "Active" if r["active"] else "Inactive"
        cls = "" if r["active"] else "inactive"
        cards += f'''
        <div class="card {cls}">
          <strong>{r["company"]}</strong> — {r["contact"]}<br>
          {r["phone"]} · {r["email"]}<br>
          Services: {r["services"]}<br>
          Status: {status}<br>
          <form method="post" action="/toggle_contractor" style="display:inline;margin-top:12px">
            <input type="hidden" name="id" value="{r["id"]}">
            <button type="submit">{ "Deactivate" if r["active"] else "Activate" }</button>
          </form>
        </div>
        '''
    return render_template_string(f"""
    {STYLE}
    <div class="container">
      <div class="card">
        <h2>Contractor Management</h2>
        <p>Activate or deactivate contractors for exclusive lead matching.</p>
        <p><a href="/">← Home</a></p>
      </div>
      {cards or '<div class="card"><p>No contractors yet.</p></div>'}
    </div>
    """)

@app.route("/toggle_contractor", methods=["POST"])
def toggle_contractor():
    cid = request.form.get("id")
    if cid:
        with get_db() as db:
            db.execute("UPDATE contractors SET active = 1 - active WHERE id = ?", (cid,))
    return redirect(url_for("contractors"))

@app.route("/contractor_login", methods=["GET", "POST"])
def contractor_login():
    if request.method == "POST":
        session["contractor_email"] = request.form.get("email")
        return redirect(url_for("home"))
    return render_template_string(f"""
    {STYLE}
    <div class="container">
      <div class="card">
        <h2>Contractor Login</h2>
        <form method="post">
          <label>Email</label><input name="email" type="email" required>
          <label>Password</label><input name="password" type="password">
          <button type="submit">Login</button>
        </form>
        <p><a href="/">← Home</a></p>
      </div>
    </div>
    """)

@app.route("/privacy")
def privacy():
    return render_template_string(f"""{STYLE}<div class="container"><div class="card"><h1>Privacy Policy</h1><p>Contractor information is used solely for account management and exclusive lead matching. Contact details are not shared with homeowners until a lead is accepted. No shared leads. Operated by Albert R LaMotte dba Restoration Contractors MN.</p><a href="/">← Home</a></div></div>""")

@app.route("/terms")
def terms():
    return render_template_string(f"""{STYLE}<div class="container"><div class="card"><h1>Terms</h1><p>Exclusive lead service operated by Albert R LaMotte dba Restoration Contractors MN. Contractors are charged only upon acceptance of a lead. All agreements are governed by Minnesota law, including the Home Solicitation Sales Act. No shared leads.</p><a href="/">← Home</a></div></div>""")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)