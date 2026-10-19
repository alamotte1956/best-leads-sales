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
            # Prefer exact ZIP or "full" area match
            if zip_code and (zip_code in area or "full" in area or "twin" in area):
                matches.append((c, 2))
            else:
                matches.append((c, 1))
    if not matches:
        return None
    matches.sort(key=lambda x: -x[1])
    return matches[0][0]
    """Return competitive price: 20% below typical Angi shared-lead rates."""
    # Typical Angi shared lead ranges (midpoint used)
    base = {
        "water_damage": 75,
        "dry_out": 65,
        "mold_mitigation": 55,
        "mold_inspection": 45,
        "mold_remediation": 70,
        "iaq_testing": 40,
        "remodeling": 60,
        "roofing": 85,
        "other": 50,
    }
    price = base.get((service_type or "").lower(), 55)
    # Urgency multiplier
    if urgency == "emergency":
        price = int(price * 1.35)
    elif urgency == "asap":
        price = int(price * 1.15)
    # Quality multiplier
    if (score or 0) >= 80:
        price = int(price * 1.2)
    elif (score or 0) >= 60:
        price = int(price * 1.05)
    # 20% discount vs Angi
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
  <p class="sub">Lead sales database — contractors & exclusive restoration leads · <strong>No shared leads.</strong> One contractor per job. · <a href="/available">Contractor Available Leads Page</a></p>
  {{ content|safe }}
</body>
</html>
"""

@app.route("/")
def home():
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
                f"License {'✓' if c['license_verified'] else '✗'} · Insurance {'✓' if c['insurance_verified'] else '✗'} · BG {'✓' if c['background_checked'] else '✗'} — "
                f"Years: {c['years_in_business'] or '—'} — Services: {c['services_offered'] or '—'} "
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

    content = f"""
    <div class="card">
      <h2>Available & Sold Leads</h2>
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
    <head><title>{c['name']} — Best Leads</title>
    <style>body{{font-family:system-ui; max-width:720px; margin:40px auto; padding:16px; background:#f8fafc;}} .card{{background:white; padding:28px; border-radius:12px;}}</style>
    </head>
    <body>
      <div class="card">
        <h1>{c['name']}</h1>
        <p>{badge_html}</p>
        <p><strong>Services:</strong> {c['services_offered'] or '—'}</p>
        <p><strong>Service Area:</strong> {c['service_area'] or '—'}</p>
        <p><strong>License:</strong> {c['license_number'] or '—'} · <strong>Insurance:</strong> {c['insurance'] or '—'}</p>
        <p><strong>Years in business:</strong> {c['years_in_business'] or '—'}</p>
        <p><strong>Leads purchased:</strong> {sold} · <strong>Average rating:</strong> {round(avg,1) if avg else 'No ratings yet'}</p>
        <h3>Reviews</h3>
        {rev_html}
        <p><a href="/available">Back to available leads</a></p>
      </div>
    </body>
    </html>
    """
    with get_db() as db:
        c = db.execute("SELECT * FROM contractors WHERE id=?", (cid,)).fetchone()
        if not c:
            return "Contractor not found", 404
        reviews = db.execute("SELECT * FROM reviews WHERE contractor_id=? ORDER BY id DESC", (cid,)).fetchall()
        avg = db.execute("SELECT AVG(rating) FROM reviews WHERE contractor_id=?", (cid,)).fetchone()[0]
    rev_html = "".join(
        f"<div style='border-bottom:1px solid #eee; padding:8px 0;'><strong>{r['rating']}/5</strong> — {r['comment'] or ''} <small>({r['created']})</small></div>"
        for r in reviews
    ) or "<p>No reviews yet.</p>"
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>{c['name']} — Best Leads</title>
    <style>body{{font-family:system-ui; max-width:700px; margin:40px auto; padding:16px;}} .card{{background:white; padding:24px; border-radius:12px;}}</style>
    </head>
    <body>
      <div class="card">
        <h1>{c['name']}</h1>
        <p><strong>Services:</strong> {c['services_offered'] or '—'}</p>
        <p><strong>Service Area:</strong> {c['service_area'] or '—'}</p>
        <p><strong>License:</strong> {c['license_number'] or '—'} · <strong>Insurance:</strong> {c['insurance'] or '—'}</p>
        <p><strong>Years in business:</strong> {c['years_in_business'] or '—'}</p>
        <p><strong>Average rating:</strong> {round(avg,1) if avg else 'No ratings yet'}</p>
        <h3>Reviews</h3>
        {rev_html}
        <p><a href="/available">Back to available leads</a></p>
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
    with get_db() as db:
        leads = db.execute("SELECT * FROM leads WHERE status='available' ORDER BY score DESC, id DESC").fetchall()
        contractors = db.execute("SELECT id, name, services_offered, service_area FROM contractors WHERE active=1").fetchall()
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
        buy_links = " ".join(
            f"<a href='/sell/{l['id']}/{c['id']}' style='margin-right:6px; background:#0ea5e9; color:white; padding:4px 8px; border-radius:4px; text-decoration:none; font-size:0.85rem;'>Buy ${l['price'] or 0}</a>"
            for _, c in matches[:3]
        ) or "No matching contractors"
        quality = "High" if (l['score'] or 0) >= 75 else "Medium" if (l['score'] or 0) >= 50 else "Standard"
        rows += f"""
        <tr>
          <td>{l['id']}</td>
          <td>{l['service_type'] or ''}<br><small>{l['urgency'] or ''}</small></td>
          <td>{l['zip'] or ''}</td>
          <td>{l['name'] or ''}<br><small>{l['phone'] or ''}</small></td>
          <td><span class="badge">{quality}</span><br>{l['score'] or ''}</td>
          <td><strong>${l['price'] or 0}</strong></td>
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
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 0.75rem; background: #dcfce7; color: #166534; }}
        a {{ color: #0ea5e9; }}
      </style>
    </head>
    <body>
      <h1>Available Exclusive Leads</h1>
      <p><strong>World-class exclusive leads.</strong> One contractor only. No shared leads like Angi or Thumbtack. Higher close rates. Competitive pricing (20% below Angi). Respond within 15 minutes for best results.</p>
      <table>
        <tr><th>ID</th><th>Service</th><th>ZIP</th><th>Contact</th><th>Quality</th><th>Price</th><th>Buy</th></tr>
        {rows}
      </table>
      <p><a href="/">Admin</a> · <a href="/signup">Become a contractor</a></p>
    </body>
    </html>
    """

@app.route("/add_lead", methods=["POST"])
def add_lead():
    d = request.form
    service = d.get("service_type")
    urgency = d.get("urgency")
    score = int(d.get("score") or 0)
    auto = calculate_auto_price(service, urgency, score)
    price = int(d.get("price") or auto)
    with get_db() as db:
        db.execute("""
            INSERT INTO leads (service_type, urgency, zip, name, phone, email, score, price, status, created)
            VALUES (?,?,?,?,?,?,?,?, 'available', ?)
        """, (
            service, urgency, d.get("zip"),
            d.get("name"), d.get("phone"), d.get("email"),
            score, price,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
    return redirect(url_for("home"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        d = request.form
        with get_db() as db:
            db.execute(
                """INSERT INTO contractors
                   (name, phone, email, service_area, license_number, insurance, insurance_expires,
                    years_in_business, services_offered, avg_job_size, preferred_contact,
                    website, google_profile, contractor_refs, exclusive_only, created)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (d.get("name"), d.get("phone"), d.get("email"), d.get("service_area"),
                 d.get("license_number"), d.get("insurance"), d.get("insurance_expires"),
                 d.get("years_in_business"), d.get("services_offered"), d.get("avg_job_size"),
                 d.get("preferred_contact"), d.get("website"), d.get("google_profile"),
                 d.get("contractor_refs"), d.get("exclusive_only"),
                 datetime.now().strftime("%Y-%m-%d %H:%M"))
            )
        return """
        <h2>Thank you!</h2>
        <p>Your contractor application has been received and is pending approval. We will contact you once reviewed.</p>
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
        input, select { width: 100%; padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; }
        button { width: 100%; background: #0ea5e9; color: white; border: none; padding: 12px; border-radius: 6px; font-size: 16px; margin-top: 16px; }
      </style>
    </head>
    <body>
      <div class="card">
        <h2>Contractor Signup</h2>
        <p>Join Best Leads to receive exclusive Twin Cities restoration leads.</p>
        <form method="POST">
          <label>Company / Contractor Name *</label>
          <input name="name" required>
          <label>Phone *</label>
          <input name="phone" required>
          <label>Email *</label>
          <input name="email" type="email" required>
          <label>License Number *</label>
          <input name="license_number" required placeholder="MN contractor license #">
          <label>Insurance Status *</label>
          <select name="insurance" required>
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

@app.route("/auto_assign/<int:lead_id>")
def auto_assign(lead_id):
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

@app.route("/sell_success/<int:lead_id>/<int:contractor_id>")
def sell_success(lead_id, contractor_id):
    with get_db() as db:
        db.execute(
            "UPDATE leads SET status='sold', sold_to=?, sold_at=? WHERE id=? AND status='available'",
            (contractor_id, datetime.now().strftime("%Y-%m-%d %H:%M"), lead_id)
        )
    return redirect(url_for("home"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
