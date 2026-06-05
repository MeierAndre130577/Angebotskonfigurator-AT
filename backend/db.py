"""
Datenbank-Layer – Supabase (Produktion) / SQLite (lokale Entwicklung)

Umgebungsvariable SUPABASE_URL gesetzt  →  Supabase wird verwendet
Keine Umgebungsvariable               →  SQLite (angebotskonfigurator.db)
"""

import os
import json
import uuid
import datetime

# ── Supabase oder SQLite? ─────────────────────────────────────────────────────

USE_SUPABASE = bool(os.environ.get("SUPABASE_URL"))

if USE_SUPABASE:
    from supabase import create_client
    _sb = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
    )
else:
    import sqlite3
    DB_PATH = os.path.join(os.path.dirname(__file__), "angebotskonfigurator.db")

    def _get_conn():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite():
        conn = _get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS customers (
                id TEXT PRIMARY KEY,
                company TEXT NOT NULL,
                contact TEXT, email TEXT, billing TEXT, delivery TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS options (
                id TEXT PRIMARY KEY,
                cluster TEXT, name TEXT NOT NULL,
                display_type TEXT, short_text TEXT, long_text TEXT,
                price REAL DEFAULT 0, recurring INTEGER DEFAULT 0,
                image_path TEXT, sort_order INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS attachments (
                id TEXT PRIMARY KEY,
                title TEXT, category TEXT, file_name TEXT, file_path TEXT,
                download_url TEXT, description TEXT, internal_note TEXT,
                selected_default INTEGER DEFAULT 0, status TEXT, last_checked TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS offers (
                id TEXT PRIMARY KEY,
                offer_no TEXT UNIQUE NOT NULL,
                project TEXT, purchase TEXT, pages TEXT, offer_items TEXT,
                status TEXT DEFAULT 'draft',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS offer_counter (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                value INTEGER DEFAULT 1000
            );
            INSERT OR IGNORE INTO offer_counter (id, value) VALUES (1, 1000);
        """)
        conn.commit()
        conn.close()

    _init_sqlite()

# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

def _new_id():
    return str(uuid.uuid4())

def _today_year():
    return datetime.date.today().year

# ── Kunden ────────────────────────────────────────────────────────────────────

def get_customers():
    if USE_SUPABASE:
        return _sb.table("customers").select("*").order("company").execute().data
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM customers ORDER BY company").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def upsert_customer(data: dict):
    if not data.get("id"):
        data["id"] = _new_id()
    if USE_SUPABASE:
        return _sb.table("customers").upsert(data).execute().data
    conn = _get_conn()
    conn.execute("""
        INSERT INTO customers (id, company, contact, email, billing, delivery)
        VALUES (:id,:company,:contact,:email,:billing,:delivery)
        ON CONFLICT(id) DO UPDATE SET
            company=excluded.company, contact=excluded.contact,
            email=excluded.email, billing=excluded.billing, delivery=excluded.delivery
    """, data)
    conn.commit(); conn.close()
    return data

def delete_customer(customer_id: str):
    if USE_SUPABASE:
        return _sb.table("customers").delete().eq("id", customer_id).execute()
    conn = _get_conn()
    conn.execute("DELETE FROM customers WHERE id=?", (customer_id,))
    conn.commit(); conn.close()

# ── Optionen ──────────────────────────────────────────────────────────────────

def get_options():
    if USE_SUPABASE:
        return _sb.table("options").select("*").order("sort_order").execute().data
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM options ORDER BY sort_order").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def upsert_option(data: dict):
    if not data.get("id"):
        data["id"] = _new_id()
    if USE_SUPABASE:
        return _sb.table("options").upsert(data).execute().data
    conn = _get_conn()
    conn.execute("""
        INSERT INTO options (id,cluster,name,display_type,short_text,long_text,
            price,recurring,image_path,sort_order)
        VALUES (:id,:cluster,:name,:display_type,:short_text,:long_text,
            :price,:recurring,:image_path,:sort_order)
        ON CONFLICT(id) DO UPDATE SET
            cluster=excluded.cluster, name=excluded.name,
            display_type=excluded.display_type, short_text=excluded.short_text,
            long_text=excluded.long_text, price=excluded.price,
            recurring=excluded.recurring, image_path=excluded.image_path,
            sort_order=excluded.sort_order
    """, data)
    conn.commit(); conn.close()
    return data

def delete_option(option_id: str):
    if USE_SUPABASE:
        return _sb.table("options").delete().eq("id", option_id).execute()
    conn = _get_conn()
    conn.execute("DELETE FROM options WHERE id=?", (option_id,))
    conn.commit(); conn.close()

# ── Anlagen ───────────────────────────────────────────────────────────────────

def get_attachments():
    if USE_SUPABASE:
        return _sb.table("attachments").select("*").execute().data
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM attachments").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def upsert_attachment(data: dict):
    if not data.get("id"):
        data["id"] = _new_id()
    if USE_SUPABASE:
        return _sb.table("attachments").upsert(data).execute().data
    conn = _get_conn()
    conn.execute("""
        INSERT INTO attachments (id,title,category,file_name,file_path,
            download_url,description,internal_note,selected_default,status)
        VALUES (:id,:title,:category,:file_name,:file_path,
            :download_url,:description,:internal_note,:selected_default,:status)
        ON CONFLICT(id) DO UPDATE SET
            title=excluded.title, category=excluded.category,
            file_name=excluded.file_name, file_path=excluded.file_path,
            download_url=excluded.download_url, description=excluded.description,
            internal_note=excluded.internal_note,
            selected_default=excluded.selected_default, status=excluded.status
    """, data)
    conn.commit(); conn.close()
    return data

def delete_attachment(attachment_id: str):
    if USE_SUPABASE:
        return _sb.table("attachments").delete().eq("id", attachment_id).execute()
    conn = _get_conn()
    conn.execute("DELETE FROM attachments WHERE id=?", (attachment_id,))
    conn.commit(); conn.close()

# ── Angebote ──────────────────────────────────────────────────────────────────

def generate_offer_number():
    year = _today_year()
    if USE_SUPABASE:
        # Supabase: atomarer Zähler via RPC (SQL-Funktion, siehe Schema)
        result = _sb.rpc("increment_offer_counter").execute()
        n = result.data
        return f"ANG-{year}-{n:04d}"
    conn = _get_conn()
    conn.execute("UPDATE offer_counter SET value = value + 1 WHERE id = 1")
    n = conn.execute("SELECT value FROM offer_counter WHERE id=1").fetchone()[0]
    conn.commit(); conn.close()
    return f"ANG-{year}-{n:04d}"

def upsert_offer(data: dict):
    if not data.get("id"):
        data["id"] = _new_id()
    data["updated_at"] = datetime.datetime.utcnow().isoformat()
    if USE_SUPABASE:
        payload = {
            "id": data["id"],
            "offer_no": data.get("offer_no"),
            "project": data.get("project"),
            "purchase": data.get("purchase"),
            "pages": data.get("pages"),
            "offer_items": data.get("offer_items"),
            "status": data.get("status", "draft"),
            "updated_at": data["updated_at"],
        }
        return _sb.table("offers").upsert(payload).execute().data
    conn = _get_conn()
    conn.execute("""
        INSERT INTO offers (id,offer_no,project,purchase,pages,offer_items,status,updated_at)
        VALUES (:id,:offer_no,:project,:purchase,:pages,:offer_items,:status,:updated_at)
        ON CONFLICT(id) DO UPDATE SET
            offer_no=excluded.offer_no, project=excluded.project,
            purchase=excluded.purchase, pages=excluded.pages,
            offer_items=excluded.offer_items, status=excluded.status,
            updated_at=excluded.updated_at
    """, {
        **data,
        "project":     json.dumps(data.get("project") or {}),
        "purchase":    json.dumps(data.get("purchase") or {}),
        "pages":       json.dumps(data.get("pages") or []),
        "offer_items": json.dumps(data.get("offer_items") or []),
    })
    conn.commit(); conn.close()
    return data

def get_offer_by_number(offer_no: str):
    if USE_SUPABASE:
        rows = _sb.table("offers").select("*").eq("offer_no", offer_no).execute().data
        return rows[0] if rows else None
    conn = _get_conn()
    row = conn.execute("SELECT * FROM offers WHERE offer_no=?", (offer_no,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    for key in ("project", "purchase", "pages", "offer_items"):
        if isinstance(d.get(key), str):
            try:
                d[key] = json.loads(d[key])
            except Exception:
                d[key] = {} if key in ("project", "purchase") else []
    return d
