"""
Best Leads — Lead Sales Database
Separate server for selling exclusive restoration leads to contractors.
SQLite database tracks contractors, available leads, and sales.
"""
from flask import Flask, render_template_string, request, redirect, url_for
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "best-leads-sales-2026"
DB = "best_leads.db"

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
            active INTEGER DEFAULT 1,
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
        # No auto-seeded contractors

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
  <p class="sub">Lead sales database — contractors & exclusive restoration leads</p>
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
        contractors = db.execute("SELECT * FROM contractors WHERE active=1").fetchall()

    rows = ""
    for l in leads:
        status_cls = "sold" if l["status"] == "sold" else "avail"
        sold = l["contractor_name"] or "—"
        rows += f"""
        <tr>
          <td>{l['id']}</td>
          <td>{l['service_type'] or ''}<br><small>{l['urgency'] or ''}</small></td>
          <td>{l['zip'] or ''}</td>
          <td>{l['name'] or ''}<br><small>{l['phone'] or ''}</small></td>
          <td>{l['score'] or ''}</td>
          <td>${l['price'] or 0}</td>
          <td><span class="badge {status_cls}">{l['status']}</span></td>
          <td>{sold}</td>
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
        <input name="price" type="number" placeholder="Price $" required>
        <button type="submit">Add Lead</button>
      </form>
    </div>
    <div class="card">
      <h2>Contractors</h2>
      <ul>
        {''.join(f"<li>{c['name']} — {c['phone']} — {c['service_area']} <a href='/delete_contractor/{c['id']}'>delete</a></li>" for c in contractors) or "<li>None yet</li>"}
      </ul>
      <p><a href="/clear_contractors" style="color:#dc2626;">Clear all contractors</a></p>
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

@app.route("/add_lead", methods=["POST"])
def add_lead():
    d = request.form
    with get_db() as db:
        db.execute("""
            INSERT INTO leads (service_type, urgency, zip, name, phone, email, score, price, status, created)
            VALUES (?,?,?,?,?,?,?,?, 'available', ?)
        """, (
            d.get("service_type"), d.get("urgency"), d.get("zip"),
            d.get("name"), d.get("phone"), d.get("email"),
            int(d.get("score") or 0), int(d.get("price") or 0),
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
    return redirect(url_for("home"))

@app.route("/add_contractor", methods=["POST"])
def add_contractor():
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
    with get_db() as db:
        db.execute("DELETE FROM contractors")
    return redirect(url_for("home"))

@app.route("/delete_contractor/<int:cid>")
def delete_contractor(cid):
    with get_db() as db:
        db.execute("DELETE FROM contractors WHERE id=?", (cid,))
    return redirect(url_for("home"))

@app.route("/sell/<int:lead_id>/<int:contractor_id>")
def sell(lead_id, contractor_id):
    with get_db() as db:
        db.execute(
            "UPDATE leads SET status='sold', sold_to=?, sold_at=? WHERE id=? AND status='available'",
            (contractor_id, datetime.now().strftime("%Y-%m-%d %H:%M"), lead_id)
        )
    return redirect(url_for("home"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
