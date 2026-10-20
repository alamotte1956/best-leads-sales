"""
Best Leads — Lead Sales Database
Separate server for selling exclusive restoration leads to contractors.
SQLite database tracks contractors, available leads, and sales.
"""
from flask import Flask, render_template_string, request, redirect, url_for
import sqlite3
from datetime import datetime
import os
import stripe

app = Flask(__name__)
app.secret_key = "best-leads-sales-2026"
DB = "best_leads.db"
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

def expire_old_assignments():
    """Return assigned leads to available if not accepted within 24 hours."""
    cutoff = (datetime.now() - __import__('datetime').timedelta(hours=24)).strftime("%Y-%m-%d %H:%M")
    with get_db() as db:
        db.execute(
            "UPDATE leads SET status='available', sold_to=NULL, sold_at=NULL WHERE status='assigned' AND sold_at < ?",
            (cutoff,)
        )

def find_best_contractor(service_type, zip_code):
    """Auto-match: approved contractor whose services include the lead type and service area covers the ZIP."""
    with get_db() as db:
        contractors = db.execute(
            "SELECT * FROM contractors WHERE status='approved' AND active=1"
        ).fetchall()
    service = (service_type or "").lower().replace("_", " ")
    matches = []
    for c in contractors:
        services = (c["services_offered"] or "").lower()
        area = (c["service_area"] or "").lower()
        if service and service in services:
            if zip_code and (zip_code in area or "full" in area or "twin" in area):
                matches.append((c, 2))
            else:
                matches.append((c, 1))
    if not matches:
        return None
    matches.sort(key=lambda x: -x[1])
    return matches[0][0]

def calculate_auto_price(service_type, urgency, score):
    """Return competitive price: 20% below typical Angi shared-lead rates."""
    base = {
        "water_damage": 75,
        "dry_out": 65,
        "mold_mitigation": 55,
        "mold_inspection": 45,
        "mold_remediation": 70,
        "iaq_testing": 40,
        "iaq": 40,
        "remodeling": 60,
        "kitchen": 70,
        "bathroom": 65,
        "addition": 80,
        "roofing": 85,
        "siding": 70,
        "windows": 60,
        "painting": 45,
        "flooring": 50,
        "hvac": 55,
        "plumbing": 50,
        "electrical": 50,
        "landscaping": 40,
        "other": 50,
    }
    price = base.get((service_type or "").lower(), 55)
    if urgency == "emergency":
        price = int(price * 1.35)
    elif urgency == "asap":
        price = int(price * 1.15)
    if (score or 0) >= 80:
        price = int(price * 1.2)
    elif (score or 0) >= 60:
        price = int(price * 1.05)
    return max(25, int(price * 0.80))

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
            email TEXT,
            service_area TEXT,
            license_number TEXT,
            insurance TEXT,
            insurance_expires TEXT,
            years_in_business TEXT,
            services_offered TEXT,
            avg_job_size TEXT,
            preferred_contact TEXT,
            website TEXT,
            google_profile TEXT,
            contractor_refs TEXT,
            exclusive_only TEXT,
            active INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            license_verified INTEGER DEFAULT 0,
            insurance_verified INTEGER DEFAULT 0,
            background_checked INTEGER DEFAULT 0,
            created TEXT
        );
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contractor_id INTEGER,
            lead_id INTEGER,
            rating INTEGER,
            comment TEXT,
            created TEXT
        );
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_type TEXT,
            urgency TEXT,
            zip TEXT,
            name TEXT,
            phone TEXT,
            email TEXT,
            score INTEGER,
            priority_level TEXT,
            price INTEGER,
            status TEXT DEFAULT 'available',
            created TEXT,
            sold_to INTEGER,
            sold_at TEXT,
            FOREIGN KEY(sold_to) REFERENCES contractors(id)
        );
        """)
        # Add new columns if they don't exist (safe for existing DBs)
        cols = [r[1] for r in db.execute("PRAGMA table_info(contractors)").fetchall()]
        for col in ["license_number", "insurance", "insurance_expires", "years_in_business",
                    "services_offered", "avg_job_size", "preferred_contact", "website",
                    "google_profile", "contractor_refs", "exclusive_only", "status", "stripe_customer_id",
                    "license_verified", "insurance_verified", "background_checked"]:
            if col not in cols:
                db.execute(f"ALTER TABLE contractors ADD COLUMN {col} TEXT")

init_db()

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Best Leads — Sales Database</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 1100px; margin: 30px auto; padding: 16px; background: #f8fafc; color: #1e293b; }
  h1 { margin: 0 0 8px; }
  .sub { color: #64748b; margin-bottom: 24px; }
  table { width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; }
  th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #e2e8f0; font-size: 0.92rem; }
  th { background: #0f172a; color: white; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 0.75rem; background: #e0f2fe; color: #0369a1; }
  .sold { background: #dcfce7; color: #166534; }
  .avail { background: #fef9c3; color: #854d0e; }
  a { color: #0ea5e9; text-decoration: none; }
  .card { background: white; padding: 16px; border-radius: 10px; margin-bottom: 20px; }
  form input, form select { padding: 8px; margin: 4px 8px 4px 0; border: 1px solid #cbd5e1; border-radius: 6px; }
  button { background: #0ea5e9; color: white; border: none; padding: 8px 14px; border-radius: 6px; cursor: pointer; }
</style>
</head>
<body>
  <h1>Best Leads</h1>
  <p class="sub">Lead sales database — contractors & exclusive restoration leads · <strong>No shared leads.</strong> One contractor per job. · <a href="/available">Contractor Available Leads Page</a> · <a href="/hub">Hub</a> · <a href="/hub/edit">Edit Hub</a></p>
  {{ content|safe }}
</body>
</html>
"""

@app.route("/")
@app.route("/admin")
def home():
    try:
        expire_old_assignments()
    except Exception:
        pass
    with get_db() as db:
        leads = db.execute("""
            SELECT l.*, c.name as contractor_name
            FROM leads l LEFT JOIN contractors c ON l.sold_to = c.id
            ORDER BY l.id DESC
        """).fetchall()
        try:
            contractors = db.execute("SELECT * FROM contractors WHERE status IN ('approved','paused') OR active=1").fetchall()
            pending = db.execute("SELECT * FROM contractors WHERE active=0 OR status='pending'").fetchall()
            contractor_html = "".join(
                f"<li><strong><a href='/contractor/{c['id']}'>{c['name']}</a></strong> — {c['phone'] or ''} — "
                f"License {'✓' if c['license_verified'] else '✗'} · Insurance {'✓' if c['insurance_verified'] else '✗'} — "
                f"Bought: {db.execute('SELECT COUNT(*) FROM leads WHERE sold_to=? AND status=\"sold\"', (c['id'],)).fetchone()[0]} — "
                f"<a href='https://secure.doli.state.mn.us/lookup/licensing.aspx' target='_blank' style='background:#0ea5e9; color:white; padding:4px 10px; border-radius:6px; text-decoration:none; font-size:0.8rem; margin-right:4px;'>Check License</a>"
                f"<a href='https://www.inslookup.doli.state.mn.us' target='_blank' style='background:#16a34a; color:white; padding:4px 10px; border-radius:6px; text-decoration:none; font-size:0.8rem; margin-right:4px;'>Check Workers Comp</a>"
                f"<a href='/toggle_contractor/{c['id']}'>{'turn off' if c['active'] else 'turn on'}</a> · "
                f"<a href='/delete_contractor/{c['id']}'>delete</a></li>"
                for c in contractors
            ) or "<li>None approved yet</li>"
            pending_html = "".join(
                f"<li><strong>{c['name']}</strong> — {c['phone'] or ''} — License: {c['license_number'] or '—'} — Insurance: {c['insurance'] or '—'} <a href='/approve_contractor/{c['id']}'>approve</a> · <a href='/delete_contractor/{c['id']}'>reject</a></li>"
                for c in pending
            ) or "<li>None pending</li>"
        except Exception:
            contractor_html = "<li>Error loading contractors</li>"
            pending_html = ""

    rows = ""
    for l in leads:
        status_cls = "sold" if l["status"] == "sold" else "avail"
        sold = l["contractor_name"] or "—"
        assign_links = ""
        if l["status"] == "available":
            assign_links = f"""<a href='/auto_assign/{l['id']}'>auto</a> · """
            for c in contractors:
                if c["status"] == "approved" and c["active"]:
                    assign_links += f"""<a href='/assign/{l['id']}/{c['id']}'>{c['name'][:12]}</a> · """
        elif l["status"] == "assigned":
            assign_links = f"""<a href='/decline/{l['id']}' style='color:#dc2626;'>decline</a>"""
        rows += f"""
        <tr>
          <td>{l['id']}</td>
          <td>{l['service_type'] or ''}<br><small>{l['urgency'] or ''}</small></td>
          <td>{l['zip'] or ''}</td>
          <td>{l['name'] or ''}<br><small>{l['phone'] or ''}</small></td>
          <td>{l['score'] or ''}</td>
          <td>${l['price'] or 0}</td>
          <td><span class="badge {status_cls}">{l['status']}</span></td>
          <td>{sold}<br><small>{assign_links}</small></td>
        </tr>"""
    if not rows:
        rows = "<tr><td colspan='8'>No leads yet. Add one below or import from the intake form.</td></tr>"

    sold_rows = ""
    sold_count = 0
    sold_revenue = 0
    for l in leads:
        if l["status"] == "sold":
            sold_count += 1
            sold_revenue += l["price"] or 0
            sold_rows += f"""
            <tr>
              <td>{l['id']}</td>
              <td>{l['service_type'] or ''}</td>
              <td>{l['name'] or ''}</td>
              <td>${l['price'] or 0}</td>
              <td>{l['contractor_name'] or '—'}</td>
              <td>{l['sold_at'] or ''}</td>
            </tr>"""
    if not sold_rows:
        sold_rows = "<tr><td colspan='6'>No leads sold yet.</td></tr>"

    content = f"""
    <div class="card">
      <h2>Verification Tools</h2>
      <p><a href="https://secure.doli.state.mn.us/lookup/licensing.aspx" target="_blank">MN License Lookup</a> · 
         <a href="https://www.inslookup.doli.state.mn.us" target="_blank">Workers Comp Verification</a></p>
      <p style="font-size:0.85rem; color:#64748b;">Use these to verify pending contractors before approving.</p>
    </div>
      <p><strong>{sold_count}</strong> leads sold · <strong>${sold_revenue}</strong> revenue</p>
    </div>
    <div class="card">
      <h2>Sold Leads</h2>
      <table>
        <tr><th>ID</th><th>Service</th><th>Homeowner</th><th>Price</th><th>Sold To</th><th>Sold At</th></tr>
        {sold_rows}
      </table>
    </div>
    <div class="card">
      <h2>All Leads</h2>
      <table>
        <tr><th>ID</th><th>Service</th><th>ZIP</th><th>Contact</th><th>Score</th><th>Price</th><th>Status</th><th>Sold To</th></tr>
        {rows}
      </table>
    </div>
    <div class="card">
      <h2>Add Lead for Sale</h2>
      <form method="POST" action="/add_lead">
        <input name="service_type" placeholder="water_damage / mold_remediation" required>
        <input name="urgency" placeholder="emergency / asap">
        <input name="zip" placeholder="ZIP" size="6">
        <input name="name" placeholder="Homeowner name">
        <input name="phone" placeholder="Phone">
        <input name="email" placeholder="Email">
        <input name="score" type="number" placeholder="Score" value="75">
        <input name="price" type="number" placeholder="Price $ (leave blank for auto)">
        <button type="submit">Add Lead</button>
        <p style="font-size:0.85rem; color:#64748b; margin-top:8px;">Leave price blank for automatic 20% below Angi rates. Or enter a number to override.</p>
      </form>
    </div>
    <div class="card">
      <h2>Contractors</h2>
      <h3>Pending Approval</h3>
      <ul>{pending_html}</ul>
      <h3>Approved</h3>
      <ul>{contractor_html}</ul>
      <p><a href="/signup">Contractor Signup Form</a> · <a href="/clear_contractors" style="color:#dc2626;">Clear all contractors</a></p>
      <form method="POST" action="/add_contractor">
        <input name="name" placeholder="Contractor name" required>
        <input name="phone" placeholder="Phone">
        <input name="email" placeholder="Email">
        <input name="service_area" placeholder="Service area">
        <button type="submit">Add Contractor</button>
      </form>
    </div>
    """
    return render_template_string(HTML, content=content)

@app.route("/contractor/<int:cid>")
def contractor_profile(cid):
    with get_db() as db:
        c = db.execute("SELECT * FROM contractors WHERE id=?", (cid,)).fetchone()
        if not c:
            return "Contractor not found", 404
        reviews = db.execute("SELECT * FROM reviews WHERE contractor_id=? ORDER BY id DESC", (cid,)).fetchall()
        avg = db.execute("SELECT AVG(rating) FROM reviews WHERE contractor_id=?", (cid,)).fetchone()[0]
        sold = db.execute("SELECT COUNT(*) FROM leads WHERE sold_to=? AND status='sold'", (cid,)).fetchone()[0]
    rev_html = "".join(
        f"<div style='border-bottom:1px solid #eee; padding:8px 0;'><strong>{r['rating']}/5</strong> — {r['comment'] or ''} <small>({r['created']})</small></div>"
        for r in reviews
    ) or "<p>No reviews yet.</p>"
    badges = []
    if c['license_verified']: badges.append("License Verified")
    if c['insurance_verified']: badges.append("Insurance Verified")
    if c['background_checked']: badges.append("Background Checked")
    if avg and avg >= 4.5: badges.append("Top Rated")
    badge_html = " · ".join(f"<span style='background:#dcfce7; color:#166534; padding:2px 8px; border-radius:999px; font-size:0.8rem;'>{b}</span>" for b in badges) or "Pending verification"
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <title>{c['name']} — Best Leads</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        body {{ font-family: system-ui; max-width: 800px; margin: 40px auto; padding: 16px; background: #f8fafc; }}
        .card {{ background: white; padding: 32px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
        .badge {{ display: inline-block; background: #dcfce7; color: #166534; padding: 4px 10px; border-radius: 999px; font-size: 0.8rem; margin-right: 6px; }}
        .stat {{ display: inline-block; margin-right: 24px; }}
        .stat strong {{ display: block; font-size: 1.4rem; }}
      </style>
    </head>
    <body>
      <div class="card">
        <h1>{c['name']}</h1>
        <p>{badge_html}</p>
        <div style="margin: 20px 0; padding: 16px; background: #f1f5f9; border-radius: 8px;">
          <span class="stat"><strong>{sold}</strong> Leads Bought</span>
          <span class="stat"><strong>{round(avg,1) if avg else '—'}</strong> Avg Rating</span>
          <span class="stat"><strong>{c['years_in_business'] or '—'}</strong> Years</span>
        </div>
        <p><strong>Services:</strong> {c['services_offered'] or '—'}</p>
        <p><strong>Service Area:</strong> {c['service_area'] or '—'}</p>
        <p><strong>License:</strong> {c['license_number'] or '—'} · <strong>Insurance:</strong> {c['insurance'] or '—'}</p>
        <h3>Reviews</h3>
        {rev_html}
        <p style="margin-top:24px;"><a href="/available">← Available Leads</a> · <a href="/">Admin</a></p>
      </div>
    </body>
    </html>
    """

@app.route("/review/<int:contractor_id>/<int:lead_id>", methods=["GET", "POST"])
def leave_review(contractor_id, lead_id):
    if request.method == "POST":
        rating = int(request.form.get("rating", 5))
        comment = request.form.get("comment", "")
        with get_db() as db:
            db.execute("INSERT INTO reviews (contractor_id, lead_id, rating, comment, created) VALUES (?,?,?,?,?)",
                       (contractor_id, lead_id, rating, comment, datetime.now().strftime("%Y-%m-%d %H:%M")))
        return "<h2>Thank you for your review!</h2><p><a href='/'>Back</a></p>"
    return f"""
    <h2>Leave a Review</h2>
    <form method="POST">
      <label>Rating (1-5)</label><br>
      <input name="rating" type="number" min="1" max="5" value="5" required><br><br>
      <label>Comment</label><br>
      <textarea name="comment" rows="4" style="width:100%;"></textarea><br>
      <button type="submit">Submit Review</button>
    </form>
    """

@app.route("/available")
def available_leads():
    expire_old_assignments()
    with get_db() as db:
        leads = db.execute("SELECT * FROM leads WHERE status IN ('available','assigned') ORDER BY score DESC, id DESC").fetchall()
        contractors = db.execute("SELECT id, name, services_offered, service_area FROM contractors WHERE active=1 AND status='approved'").fetchall()
    rows = ""
    for l in leads:
        matches = []
        for c in contractors:
            match_score = 0
            if l['service_type'] and c['services_offered'] and l['service_type'].lower() in (c['services_offered'] or '').lower():
                match_score += 2
            if l['zip'] and c['service_area'] and l['zip'] in (c['service_area'] or ''):
                match_score += 1
            if match_score > 0:
                matches.append((match_score, c))
        matches.sort(key=lambda x: -x[0])
        quality = "High" if (l['score'] or 0) >= 75 else "Medium" if (l['score'] or 0) >= 50 else "Standard"
        quality_color = "#166534" if quality == "High" else "#854d0e" if quality == "Medium" else "#64748b"
        if l["status"] == "available":
            buy_links = " ".join(
                f"<a href='/sell/{l['id']}/{c['id']}' style='margin-right:6px; background:#0ea5e9; color:white; padding:6px 12px; border-radius:6px; text-decoration:none; font-size:0.85rem; font-weight:600;'>Buy ${l['price'] or 0}</a>"
                for _, c in matches[:3]
            ) or "<span style='color:#64748b;'>No matching contractors</span>"
            status_html = f"<span style='background:#dcfce7; color:#166534; padding:2px 8px; border-radius:999px; font-size:0.75rem;'>Available</span>"
        else:
            buy_links = f"<a href='/accept/{l['id']}' style='background:#16a34a; color:white; padding:6px 12px; border-radius:6px; text-decoration:none; font-size:0.85rem; font-weight:600; margin-right:6px;'>Accept</a> <a href='/decline/{l['id']}' style='color:#dc2626; font-weight:600;'>Reject</a>"
            status_html = f"<span style='background:#fef3c7; color:#854d0e; padding:2px 8px; border-radius:999px; font-size:0.75rem;'>Assigned</span>"
        rows += f"""
        <tr>
          <td>{l['id']}</td>
          <td><strong>{l['service_type'] or ''}</strong><br><small style='color:#64748b;'>{l['urgency'] or ''}</small></td>
          <td>{l['zip'] or ''}</td>
          <td><span style='color:#64748b;'>Hidden until purchase</span></td>
          <td><span style='background:{quality_color}22; color:{quality_color}; padding:2px 8px; border-radius:999px; font-size:0.75rem; font-weight:600;'>{quality}</span><br><small>{l['score'] or ''}</small></td>
          <td><strong style='font-size:1.1rem;'>${l['price'] or 0}</strong></td>
          <td>{status_html}</td>
          <td>{buy_links}</td>
        </tr>"""
    if not rows:
        rows = "<tr><td colspan='7'>No available leads right now.</td></tr>"
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Available Exclusive Leads — Best Leads</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        body {{ font-family: system-ui; max-width: 1100px; margin: 30px auto; padding: 16px; background: #f8fafc; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; }}
        th, td {{ padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: left; font-size: 0.9rem; }}
        th {{ background: #0f172a; color: white; }}
        @media (max-width: 600px) {{
          body {{ padding: 8px; margin: 10px auto; }}
          table {{ font-size: 0.8rem; }}
          th, td {{ padding: 6px; }}
          h1 {{ font-size: 1.4rem; }}
        }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 0.75rem; background: #dcfce7; color: #166534; }}
        a {{ color: #0ea5e9; }}
      </style>
    </head>
    <body>
      <h1>Available Exclusive Leads</h1>
      <p><strong>World-class exclusive leads.</strong> One contractor only. No shared leads like Angi. Higher close rates. Competitive pricing (20% below Angi). Volume discount: 10% off after 10 leads/month. Respond within 15 minutes.</p>
      <p style="background:#fee2e2; color:#991b1b; padding:10px 14px; border-radius:8px; font-weight:600;">Leads expire after 24 hours if not accepted.</p>
      <table>
        <tr><th>ID</th><th>Service</th><th>ZIP</th><th>Contact</th><th>Quality</th><th>Price</th><th>Status</th><th>Buy</th></tr>
        {rows}
      </table>
      <p><a href="/">Admin</a> · <a href="/signup">Become a contractor</a></p>
    </body>
    </html>
    """

@app.route("/seed_demo")
def seed_demo():
    """Add demo contractors and leads for testing both sides."""
    with get_db() as db:
        contractors = [
            ("Twin Cities Roofing", "612-555-0101", "roof@example.com", "55416, 55345", "MN-ROOF-123", "Yes — Liability & Workers Comp", "2027-01-01", "12", "roofing, siding", "approved", 1),
            ("Minneapolis Mold Pros", "612-555-0102", "mold@example.com", "55406, 55407", "MN-MOLD-456", "Yes — Liability & Workers Comp", "2026-12-15", "8", "mold_remediation, water_damage", "approved", 1),
            ("Suburban Remodel Co", "952-555-0103", "remodel@example.com", "55345, 55331", "MN-REM-789", "Yes — Liability only", "2026-11-01", "15", "remodeling, kitchen, bathroom", "pending", 0),
            ("West Metro Windows", "952-555-0104", "windows@example.com", "55345, 55316", "MN-WIN-321", "Yes — Liability & Workers Comp", "2027-03-01", "6", "windows, siding", "approved", 1),
            ("Emergency Dry Out", "612-555-0105", "dry@example.com", "full twin cities", "MN-DRY-654", "Yes — Liability & Workers Comp", "2026-10-01", "10", "dry_out, water_damage", "approved", 1),
        ]
        for c in contractors:
            db.execute("""
                INSERT INTO contractors (name, phone, email, service_area, license_number, insurance, insurance_expires, years_in_business, services_offered, status, active, created)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (*c, datetime.now().strftime("%Y-%m-%d %H:%M")))

        leads = [
            ("water_damage", "emergency", "55416", "Alex Rivera", "612-555-2001", "alex@example.com", 88, 81, "Minneapolis Mold Pros"),
            ("mold_remediation", "asap", "55345", "Chris Patel", "952-555-2002", "chris@example.com", 75, 56, "Minneapolis Mold Pros"),
            ("roofing", "this_week", "55406", "Taylor Kim", "612-555-2003", "taylor@example.com", 62, 68, "Twin Cities Roofing"),
            ("kitchen", "asap", "55331", "Jordan Lee", "952-555-2004", "jordan@example.com", 70, 56, "Suburban Remodel Co"),
            ("windows", "this_week", "55316", "Morgan Chen", "612-555-2005", "morgan@example.com", 58, 48, "West Metro Windows"),
            ("hvac", "asap", "55407", "Riley Brooks", "952-555-2006", "riley@example.com", 80, 44, None),
            ("plumbing", "emergency", "55408", "Casey Nguyen", "612-555-2007", "casey@example.com", 85, 50, None),
        ]
        for service, urgency, zipc, name, phone, email, score, price, contractor_name in leads:
            cur = db.execute("""
                INSERT INTO leads (service_type, urgency, zip, name, phone, email, score, price, status, created)
                VALUES (?,?,?,?,?,?,?,?, 'available', ?)
            """, (service, urgency, zipc, name, phone, email, score, price, datetime.now().strftime("%Y-%m-%d %H:%M")))
            lead_id = cur.lastrowid
            if contractor_name:
                c = db.execute("SELECT id FROM contractors WHERE name=?", (contractor_name,)).fetchone()
                if c:
                    db.execute(
                        "UPDATE leads SET status='sold', sold_to=?, sold_at=? WHERE id=?",
                        (c["id"], datetime.now().strftime("%Y-%m-%d %H:%M"), lead_id)
                    )

    return """
    <h2>Demo data added</h2>
    <p>5 contractors and 7 leads created. 5 are matched to contractors.</p>
    <p><a href="/admin">Admin</a> · <a href="/available">Available leads</a></p>
    <p>Test the consumer form at:<br>
    <a href="https://web-production-ac750.up.railway.app/" target="_blank">https://web-production-ac750.up.railway.app/</a></p>
    """

@app.route("/add_demo_leads")
def add_demo_leads():
    """Add 7 exclusive demo leads for testing."""
    with get_db() as db:
        leads = [
            ("water_damage", "emergency", "55416", "Alex Rivera", "612-555-2001", "alex@example.com", 88, 81),
            ("mold_remediation", "asap", "55345", "Chris Patel", "952-555-2002", "chris@example.com", 75, 56),
            ("roofing", "this_week", "55406", "Taylor Kim", "612-555-2003", "taylor@example.com", 62, 68),
            ("kitchen", "asap", "55331", "Jordan Lee", "952-555-2004", "jordan@example.com", 70, 56),
            ("windows", "this_week", "55316", "Morgan Chen", "612-555-2005", "morgan@example.com", 58, 48),
            ("hvac", "asap", "55407", "Riley Brooks", "952-555-2006", "riley@example.com", 80, 44),
            ("plumbing", "emergency", "55408", "Casey Nguyen", "612-555-2007", "casey@example.com", 85, 50),
        ]
        for l in leads:
            db.execute("""
                INSERT INTO leads (service_type, urgency, zip, name, phone, email, score, price, status, created)
                VALUES (?,?,?,?,?,?,?,?, 'available', ?)
            """, (*l, datetime.now().strftime("%Y-%m-%d %H:%M")))
    return """
    <h2>7 demo leads added</h2>
    <p><a href="/available">View available leads</a> · <a href="/admin">Admin</a></p>
    """
    """Add demo contractors and leads for testing."""
    with get_db() as db:
        # Demo contractors
        contractors = [
            ("Twin Cities Roofing", "612-555-0101", "roof@example.com", "55416, 55345", "MN-ROOF-123", "Yes — Liability & Workers Comp", "2027-01-01", "12", "roofing, siding", "approved", 1),
            ("Minneapolis Mold Pros", "612-555-0102", "mold@example.com", "55406, 55407", "MN-MOLD-456", "Yes — Liability & Workers Comp", "2026-12-15", "8", "mold_remediation, water_damage", "approved", 1),
            ("Suburban Remodel Co", "952-555-0103", "remodel@example.com", "55345, 55331", "MN-REM-789", "Yes — Liability only", "2026-11-01", "15", "remodeling, kitchen, bathroom", "pending", 0),
            ("West Metro Windows", "952-555-0104", "windows@example.com", "55345, 55316", "MN-WIN-321", "Yes — Liability & Workers Comp", "2027-03-01", "6", "windows, siding", "approved", 1),
            ("Emergency Dry Out", "612-555-0105", "dry@example.com", "full twin cities", "MN-DRY-654", "Yes — Liability & Workers Comp", "2026-10-01", "10", "dry_out, water_damage", "approved", 1),
        ]
        for c in contractors:
            db.execute("""
                INSERT INTO contractors (name, phone, email, service_area, license_number, insurance, insurance_expires, years_in_business, services_offered, status, active, created)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (*c, datetime.now().strftime("%Y-%m-%d %H:%M")))

        # Demo leads
        leads = [
            ("roofing", "asap", "55345", "Jane Smith", "612-555-1001", "jane@example.com", 82, 68),
            ("water_damage", "emergency", "55406", "John Doe", "612-555-1002", "john@example.com", 90, 81),
            ("mold_remediation", "this_week", "55416", "Mary Johnson", "952-555-1003", "mary@example.com", 65, 56),
            ("kitchen", "asap", "55331", "Bob Wilson", "952-555-1004", "bob@example.com", 70, 56),
            ("windows", "this_week", "55316", "Sara Lee", "612-555-1005", "sara@example.com", 55, 48),
        ]
        for l in leads:
            db.execute("""
                INSERT INTO leads (service_type, urgency, zip, name, phone, email, score, price, status, created)
                VALUES (?,?,?,?,?,?,?,?, 'available', ?)
            """, (*l, datetime.now().strftime("%Y-%m-%d %H:%M")))

    return """
    <h2>Demo data added</h2>
    <p>5 contractors and 5 leads created.</p>
    <p><a href="/admin">View admin</a> · <a href="/available">View available leads</a></p>
    """
    d = request.form
    service = d.get("service_type")
    urgency = d.get("urgency")
    score = int(d.get("score") or 0)
    auto = calculate_auto_price(service, urgency, score)
    price = int(d.get("price") or auto)
    with get_db() as db:
        cur = db.execute("""
            INSERT INTO leads (service_type, urgency, zip, name, phone, email, score, price, status, created)
            VALUES (?,?,?,?,?,?,?,?, 'available', ?)
        """, (
            service, urgency, d.get("zip"),
            d.get("name"), d.get("phone"), d.get("email"),
            score, price,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
        lead_id = cur.lastrowid
    # Auto-assign if a match exists and create payment link
    match = find_best_contractor(service, d.get("zip"))
    payment_url = None
    if match and score >= 50:
        with get_db() as db:
            db.execute(
                "UPDATE leads SET status='assigned', sold_to=?, sold_at=? WHERE id=?",
                (match["id"], datetime.now().strftime("%Y-%m-%d %H:%M"), lead_id)
            )
        # Create Stripe Checkout for the contractor to pay
        if stripe.api_key and price > 0:
            try:
                session = stripe.checkout.Session.create(
                    mode="payment",
                    line_items=[{
                        "price_data": {
                            "currency": "usd",
                            "product_data": {"name": f"Exclusive Lead #{lead_id} — {service}"},
                            "unit_amount": int(price * 100),
                        },
                        "quantity": 1,
                    }],
                    success_url=request.host_url + f"sell_success/{lead_id}/{match['id']}?session_id={{CHECKOUT_SESSION_ID}}",
                    cancel_url=request.host_url,
                    metadata={"lead_id": lead_id, "contractor_id": match["id"]},
                )
                payment_url = session.url
            except Exception:
                payment_url = None
    return redirect(url_for("home"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        d = request.form
        has_license = bool(d.get("license_number"))
        has_insurance = d.get("insurance", "").startswith("Yes")
        years = int(d.get("years_in_business") or 0)
        status = "approved" if (has_license and has_insurance and years >= 3) else "pending"
        active = 1 if status == "approved" else 0

        # Save insurance certificate if uploaded
        insurance_file = request.files.get("insurance_cert")
        insurance_path = None
        if insurance_file and insurance_file.filename:
            os.makedirs("uploads", exist_ok=True)
            filename = f"ins_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{insurance_file.filename}"
            insurance_path = os.path.join("uploads", filename)
            insurance_file.save(insurance_path)

        with get_db() as db:
            db.execute(
                """INSERT INTO contractors
                   (name, phone, email, service_area, license_number, insurance, insurance_expires,
                    years_in_business, services_offered, avg_job_size, preferred_contact,
                    website, google_profile, contractor_refs, exclusive_only, status, active, created)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (d.get("name"), d.get("phone"), d.get("email"), d.get("service_area"),
                 d.get("license_number"), d.get("insurance"), d.get("insurance_expires"),
                 d.get("years_in_business"), d.get("services_offered"), d.get("avg_job_size"),
                 d.get("preferred_contact"), d.get("website"), d.get("google_profile"),
                 d.get("contractor_refs"), d.get("exclusive_only"), status, active,
                 datetime.now().strftime("%Y-%m-%d %H:%M"))
            )
        msg = "approved and can receive leads" if status == "approved" else "pending review"
        return f"""
        <h2>Thank you!</h2>
        <p>Your contractor application has been received and is {msg}.</p>
        <p><a href="/signup">Submit another</a></p>
        """
    return """
    <!DOCTYPE html>
    <html>
    <head>
      <title>Contractor Signup — Best Leads</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        body { font-family: system-ui; max-width: 520px; margin: 40px auto; padding: 16px; background: #f8fafc; }
        .card { background: white; padding: 28px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); }
        label { display: block; margin: 14px 0 4px; font-weight: 600; }
        input, select { width: 100%; padding: 12px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 16px; }
        button { width: 100%; background: #0ea5e9; color: white; border: none; padding: 14px; border-radius: 6px; font-size: 16px; margin-top: 16px; }
        @media (max-width: 600px) {
          body { margin: 10px auto; padding: 8px; }
          .card { padding: 16px; }
        }
      </style>
    </head>
    <body>
      <div class="card">
        <h2>Contractor Signup</h2>
        <p>Join Best Leads to receive exclusive Twin Cities restoration leads.</p>
        <p style="background:#dbeafe; color:#1e40af; padding:10px; border-radius:6px; font-size:0.9rem;"><strong>Verification:</strong> We check MN contractor licenses and workers comp through the official DLI lookup. Auto-approval requires license + insurance + 3+ years in business.</p>
        <form method="POST" enctype="multipart/form-data">
          <label>Company / Contractor Name *</label>
          <input name="name" required>
          <label>Phone *</label>
          <input name="phone" required>
          <label>Email *</label>
          <input name="email" type="email" required>
          <label>License Number *</label>
          <input name="license_number" required placeholder="MN contractor license #">
          <label>Liability Insurance Certificate *</label>
          <input type="file" name="insurance_cert" accept=".pdf,.jpg,.jpeg,.png" required>
          <small style="color:#64748b;">Upload certificate of insurance (PDF or image)</small>
            <option value="">Select...</option>
            <option value="Yes — Liability & Workers Comp">Yes — Liability & Workers Comp</option>
            <option value="Yes — Liability only">Yes — Liability only</option>
            <option value="No">No</option>
          </select>
          <label>Insurance Expiration Date</label>
          <input name="insurance_expires" type="date">
          <label>Years in Business *</label>
          <input name="years_in_business" type="number" min="0" required>
          <label>Services Offered *</label>
          <input name="services_offered" required placeholder="e.g. water damage, mold, remodeling, roofing">
          <label>Service Area *</label>
          <input name="service_area" required placeholder="e.g. Full Twin Cities, Bloomington, Eagan, etc.">
          <label>Average Job Size</label>
          <select name="avg_job_size">
            <option value="">Select...</option>
            <option value="Under $2,000">Under $2,000</option>
            <option value="$2,000 – $5,000">$2,000 – $5,000</option>
            <option value="$5,000 – $15,000">$5,000 – $15,000</option>
            <option value="$15,000+">$15,000+</option>
          </select>
          <label>Preferred Contact Method</label>
          <select name="preferred_contact">
            <option value="Phone">Phone</option>
            <option value="Text">Text</option>
            <option value="Email">Email</option>
          </select>
          <label>Website</label>
          <input name="website" placeholder="https://">
          <label>Google Business Profile URL</label>
          <input name="google_profile" placeholder="https://g.page/...">
          <label>References or Portfolio Link</label>
          <input name="contractor_refs" placeholder="Link or short description">
          <label>Do you want exclusive leads only?</label>
          <select name="exclusive_only">
            <option value="Yes">Yes — exclusive only</option>
            <option value="Open to shared later">Open to shared later</option>
          </select>
          <button type="submit">Apply</button>
        </form>
      </div>
    </body>
    </html>
    """
    d = request.form
    with get_db() as db:
        db.execute(
            "INSERT INTO contractors (name, phone, email, service_area, created) VALUES (?,?,?,?,?)",
            (d.get("name"), d.get("phone"), d.get("email"), d.get("service_area"),
             datetime.now().strftime("%Y-%m-%d %H:%M"))
        )
    return redirect(url_for("home"))

@app.route("/clear_contractors")
def clear_contractors():
    return """
    <h2>Clear all contractors?</h2>
    <p>This will delete every contractor (approved, paused, and pending).</p>
    <p><a href="/clear_contractors/confirm" style="color:#dc2626; font-weight:bold;">Yes, delete all contractors</a></p>
    <p><a href="/">Cancel</a></p>
    """

@app.route("/clear_contractors/confirm")
def clear_contractors_confirm():
    return """
    <h2>Are you absolutely sure?</h2>
    <p>This cannot be undone. All contractor records will be permanently deleted.</p>
    <p><a href="/clear_contractors/final" style="color:#dc2626; font-weight:bold;">Yes, permanently delete all</a></p>
    <p><a href="/">Cancel</a></p>
    """

@app.route("/clear_contractors/final")
def clear_contractors_final():
    with get_db() as db:
        db.execute("DELETE FROM contractors")
    return redirect(url_for("home"))

@app.route("/toggle_contractor/<int:cid>")
def toggle_contractor(cid):
    with get_db() as db:
        row = db.execute("SELECT active FROM contractors WHERE id=?", (cid,)).fetchone()
        if row:
            new_active = 0 if row["active"] else 1
            new_status = "approved" if new_active else "paused"
            db.execute("UPDATE contractors SET active=?, status=? WHERE id=?", (new_active, new_status, cid))
    return redirect(url_for("home"))

@app.route("/verify/<int:cid>/<field>")
def verify_field(cid, field):
    allowed = {"license": "license_verified", "insurance": "insurance_verified", "background": "background_checked"}
    col = allowed.get(field)
    if not col:
        return redirect(url_for("home"))
    with get_db() as db:
        db.execute(f"UPDATE contractors SET {col}=1 WHERE id=?", (cid,))
    return redirect(url_for("home"))

@app.route("/approve_contractor/<int:cid>")
def approve_contractor(cid):
    with get_db() as db:
        db.execute("UPDATE contractors SET active=1, status='approved' WHERE id=?", (cid,))
    return redirect(url_for("home"))

@app.route("/delete_contractor/<int:cid>")
def delete_contractor(cid):
    with get_db() as db:
        db.execute("DELETE FROM contractors WHERE id=?", (cid,))
    return redirect(url_for("home"))
    with get_db() as db:
        db.execute("DELETE FROM contractors WHERE id=?", (cid,))
    return redirect(url_for("home"))

@app.route("/assign/<int:lead_id>/<int:contractor_id>")
def assign_lead(lead_id, contractor_id):
    with get_db() as db:
        db.execute(
            "UPDATE leads SET status='assigned', sold_to=?, sold_at=? WHERE id=? AND status='available'",
            (contractor_id, datetime.now().strftime("%Y-%m-%d %H:%M"), lead_id)
        )
    return redirect(url_for("home"))

@app.route("/accept/<int:lead_id>")
def accept_lead(lead_id):
    """Contractor accepts an assigned lead."""
    with get_db() as db:
        db.execute(
            "UPDATE leads SET status='sold', sold_at=? WHERE id=? AND status='assigned'",
            (datetime.now().strftime("%Y-%m-%d %H:%M"), lead_id)
        )
    return redirect("/available")

@app.route("/decline/<int:lead_id>")
def decline_lead(lead_id):
    """Contractor refuses the assignment. Lead returns to available."""
    with get_db() as db:
        db.execute(
            "UPDATE leads SET status='available', sold_to=NULL, sold_at=NULL WHERE id=? AND status='assigned'",
            (lead_id,)
        )
    return redirect(url_for("home"))
    with get_db() as db:
        lead = db.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
    if not lead:
        return "Lead not found", 404
    match = find_best_contractor(lead["service_type"], lead["zip"])
    if not match:
        return redirect(url_for("home"))
    with get_db() as db:
        db.execute(
            "UPDATE leads SET status='assigned', sold_to=?, sold_at=? WHERE id=?",
            (match["id"], datetime.now().strftime("%Y-%m-%d %H:%M"), lead_id)
        )
    # Create payment link
    if stripe.api_key and lead["price"] and lead["price"] > 0:
        try:
            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": f"Exclusive Lead #{lead_id}"},
                        "unit_amount": int(lead["price"] * 100),
                    },
                    "quantity": 1,
                }],
                success_url=request.host_url + f"sell_success/{lead_id}/{match['id']}?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=request.host_url,
                metadata={"lead_id": lead_id, "contractor_id": match["id"]},
            )
            return redirect(session.url)
        except Exception:
            pass
    return redirect(url_for("home"))
    if not stripe.api_key:
        # No Stripe key — sell without charging
        with get_db() as db:
            db.execute(
                "UPDATE leads SET status='sold', sold_to=?, sold_at=? WHERE id=? AND status='available'",
                (contractor_id, datetime.now().strftime("%Y-%m-%d %H:%M"), lead_id)
            )
        return redirect(url_for("home"))

    with get_db() as db:
        lead = db.execute("SELECT * FROM leads WHERE id=? AND status='available'", (lead_id,)).fetchone()
        contractor = db.execute("SELECT * FROM contractors WHERE id=? AND active=1", (contractor_id,)).fetchone()
    if not lead or not contractor:
        return redirect(url_for("home"))

    # Create Stripe Checkout session for the lead price
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"Exclusive Lead #{lead_id} — {lead['service_type'] or 'Restoration'}"},
                "unit_amount": int(lead["price"] or 0) * 100,
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=request.host_url + f"sell_success/{lead_id}/{contractor_id}?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=request.host_url,
        metadata={"lead_id": str(lead_id), "contractor_id": str(contractor_id)},
    )
    return redirect(session.url, code=303)

@app.route("/sell/<int:lead_id>/<int:contractor_id>")
def sell_lead(lead_id, contractor_id):
    """Demo buy: mark lead as sold without real payment."""
    with get_db() as db:
        lead = db.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
        contractor = db.execute("SELECT * FROM contractors WHERE id=?", (contractor_id,)).fetchone()
        if not lead or not contractor:
            return "Lead or contractor not found", 404
        if lead["status"] != "available":
            return "Lead is no longer available", 400
        # Demo mode: mark as sold immediately
        db.execute(
            "UPDATE leads SET status='sold', sold_to=?, sold_at=? WHERE id=?",
            (contractor_id, datetime.now().strftime("%Y-%m-%d %H:%M"), lead_id)
        )
    return f"""
    <h2>Lead purchased (demo)</h2>
    <p>Lead #{lead_id} sold to {contractor['name']}.</p>
    <p><strong>Contact:</strong> {lead['name']} — {lead['phone']}</p>
    <p><a href="/available">Back to available leads</a> · <a href="/admin">Admin</a></p>
    """

@app.route("/sell_success/<int:lead_id>/<int:contractor_id>")
def sell_success(lead_id, contractor_id):
    with get_db() as db:
        db.execute(
            "UPDATE leads SET status='sold', sold_to=?, sold_at=? WHERE id=? AND status='available'",
            (contractor_id, datetime.now().strftime("%Y-%m-%d %H:%M"), lead_id)
        )
    return redirect(url_for("home"))

@app.route("/hub")
def hub():
    with get_db() as db:
        try:
            row = db.execute("SELECT content FROM hub_content ORDER BY id DESC LIMIT 1").fetchone()
            if row and row["content"]:
                return row["content"]
        except Exception:
            pass
    return default_hub_html()

@app.route("/hub/edit", methods=["GET", "POST"])
def hub_edit():
    if request.method == "POST":
        content = request.form.get("content", "")
        with get_db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS hub_content (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, updated TEXT)")
            db.execute("INSERT INTO hub_content (content, updated) VALUES (?, ?)",
                       (content, datetime.now().strftime("%Y-%m-%d %H:%M")))
        return redirect("/hub")
    current = default_hub_html()
    try:
        with get_db() as db:
            row = db.execute("SELECT content FROM hub_content ORDER BY id DESC LIMIT 1").fetchone()
            if row and row["content"]:
                current = row["content"]
    except Exception:
        pass
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Edit Hub</title>
      <style>
        body {{ font-family: system-ui; max-width: 900px; margin: 40px auto; padding: 16px; background: #f8fafc; }}
        textarea {{ width: 100%; height: 400px; font-family: monospace; font-size: 13px; padding: 12px; border: 1px solid #cbd5e1; border-radius: 8px; }}
        button {{ background: #0ea5e9; color: white; border: none; padding: 12px 24px; border-radius: 6px; margin-top: 12px; cursor: pointer; }}
      </style>
    </head>
    <body>
      <h2>Edit Hub Page</h2>
      <form method="POST">
        <textarea name="content">{current}</textarea>
        <br><button type="submit">Save</button>
      </form>
      <p><a href="/hub">View hub</a> · <a href="/admin">Admin</a></p>
    </body>
    </html>
    """

def default_hub_html():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Best Leads — System Hub</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; background: #f8fafc; margin: 0; padding: 40px 16px; color: #0f172a; }
    .wrap { max-width: 640px; margin: 0 auto; }
    h1 { font-size: 1.8rem; margin-bottom: 8px; }
    .sub { color: #64748b; margin-bottom: 32px; }
    .section { background: white; border-radius: 12px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
    h2 { font-size: 1.1rem; margin: 0 0 12px; color: #0369a1; }
    a { display: block; padding: 10px 12px; border-radius: 8px; text-decoration: none; color: #0f172a; margin-bottom: 4px; }
    a:hover { background: #f1f5f9; }
    .label { font-weight: 600; }
    .url { font-size: 0.8rem; color: #64748b; }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Best Leads</h1>
    <p class="sub">System hub — all links in one place</p>
    <div class="section">
      <h2>Homeowners</h2>
      <a href="https://web-production-ac750.up.railway.app/">
        <div class="label">Submit a Request</div>
        <div class="url">web-production-ac750.up.railway.app</div>
      </a>
    </div>
    <div class="section">
      <h2>Contractors</h2>
      <a href="https://best-leads-sales-production.up.railway.app/signup">
        <div class="label">Sign Up as a Contractor</div>
        <div class="url">best-leads-sales-production.up.railway.app/signup</div>
      </a>
      <a href="https://best-leads-sales-production.up.railway.app/available">
        <div class="label">Available Exclusive Leads</div>
        <div class="url">best-leads-sales-production.up.railway.app/available</div>
      </a>
    </div>
    <div class="section">
      <h2>Admin</h2>
      <a href="https://best-leads-sales-production.up.railway.app/admin">
        <div class="label">Admin Dashboard</div>
        <div class="url">best-leads-sales-production.up.railway.app/admin</div>
      </a>
    </div>
  </div>
</body>
</html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
