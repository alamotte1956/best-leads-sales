# Best Leads — Sales Database

Separate server for selling exclusive restoration leads to contractors.

## Files
- `best_leads_sales.py` — Flask app with SQLite database
- `sales_page_leads.html` — one-page sales page for contractors
- `requirements.txt` — Flask, gunicorn
- `Procfile.sales` — Railway start command (rename to Procfile if needed)

## Run locally
```bash
pip install -r requirements.txt
python best_leads_sales.py
```
Open http://127.0.0.1:5001

## Railway
Set start command to:
```
gunicorn best_leads_sales:app
```

## Database
SQLite file `best_leads.db` is created on first run.
Tables: contractors, leads (available / sold).
