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
                documents TEXT DEFAULT '[]',
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                option_ids TEXT DEFAULT '[]',
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

    def _migrate_sqlite():
        conn = _get_conn()
        existing = [row[1] for row in conn.execute("PRAGMA table_info(customers)").fetchall()]
        new_cols = {
            "position":      'TEXT DEFAULT ""',
            "phone":         'TEXT DEFAULT ""',
            "mobile":        'TEXT DEFAULT ""',
            "street":        'TEXT DEFAULT ""',
            "zip":           'TEXT DEFAULT ""',
            "city":          'TEXT DEFAULT ""',
            "website":       'TEXT DEFAULT ""',
            "card_image_url":'TEXT DEFAULT ""',
            "logo_url":      'TEXT DEFAULT ""',
        }
        for col, defn in new_cols.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE customers ADD COLUMN {col} {defn}")
        conn.commit(); conn.close()

    _migrate_sqlite()

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

def get_customer_by_email(email: str):
    if not email:
        return None
    if USE_SUPABASE:
        rows = _sb.table("customers").select("*").eq("email", email).execute().data
        return rows[0] if rows else None
    conn = _get_conn()
    row = conn.execute("SELECT * FROM customers WHERE email=?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None

def upsert_customer(data: dict):
    for f in ["position", "phone", "mobile", "street", "zip", "city", "website", "card_image_url", "logo_url"]:
        data.setdefault(f, "")
    # Deduplizierung über E-Mail
    if not data.get("id") and data.get("email"):
        existing = get_customer_by_email(data["email"])
        if existing:
            data["id"] = existing["id"]
    if not data.get("id"):
        data["id"] = _new_id()
    if USE_SUPABASE:
        return _sb.table("customers").upsert(data).execute().data
    conn = _get_conn()
    conn.execute("""
        INSERT INTO customers (id, company, contact, email, billing, delivery,
            position, phone, mobile, street, zip, city, website, card_image_url, logo_url)
        VALUES (:id,:company,:contact,:email,:billing,:delivery,
            :position,:phone,:mobile,:street,:zip,:city,:website,:card_image_url,:logo_url)
        ON CONFLICT(id) DO UPDATE SET
            company=excluded.company, contact=excluded.contact,
            email=excluded.email, billing=excluded.billing, delivery=excluded.delivery,
            position=excluded.position, phone=excluded.phone, mobile=excluded.mobile,
            street=excluded.street, zip=excluded.zip, city=excluded.city,
            website=excluded.website, card_image_url=excluded.card_image_url,
            logo_url=excluded.logo_url
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
    result = []
    for r in rows:
        d = dict(r)
        if isinstance(d.get("documents"), str):
            try: d["documents"] = json.loads(d["documents"])
            except: d["documents"] = []
        result.append(d)
    return result

def upsert_option(data: dict):
    if not data.get("id"):
        data["id"] = _new_id()
    # Dokumente als JSON serialisieren
    docs = data.get("documents") or []
    if isinstance(docs, list):
        data["documents"] = docs  # Supabase erwartet native Liste (jsonb)
    if USE_SUPABASE:
        return _sb.table("options").upsert(data).execute().data
    # SQLite: documents als JSON-String
    sqlite_data = {
        **data,
        "documents":     json.dumps(docs),
        "active":        1 if data.get('active', True) else 0,
        "price_editable": 1 if data.get('price_editable', False) else 0,
        "price_hint":    data.get('price_hint', '') or '',
    }
    conn = _get_conn()
    # Spalten nachrüsten falls noch nicht vorhanden (Migration)
    existing = {r[1] for r in conn.execute("PRAGMA table_info(options)").fetchall()}
    if "price_editable" not in existing:
        conn.execute("ALTER TABLE options ADD COLUMN price_editable INTEGER DEFAULT 0")
    if "price_hint" not in existing:
        conn.execute("ALTER TABLE options ADD COLUMN price_hint TEXT DEFAULT ''")
    conn.execute("""
        INSERT INTO options (id,cluster,name,display_type,short_text,long_text,
            price,recurring,image_path,sort_order,documents,active,price_editable,price_hint)
        VALUES (:id,:cluster,:name,:display_type,:short_text,:long_text,
            :price,:recurring,:image_path,:sort_order,:documents,:active,
            :price_editable,:price_hint)
        ON CONFLICT(id) DO UPDATE SET
            cluster=excluded.cluster, name=excluded.name,
            display_type=excluded.display_type, short_text=excluded.short_text,
            long_text=excluded.long_text, price=excluded.price,
            recurring=excluded.recurring, image_path=excluded.image_path,
            sort_order=excluded.sort_order, documents=excluded.documents,
            active=excluded.active, price_editable=excluded.price_editable,
            price_hint=excluded.price_hint
    """, sqlite_data)
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
    import random, string, datetime
    now   = datetime.datetime.now()
    year  = now.strftime('%Y')
    month = now.strftime('%m')
    rnd   = ''.join(random.choices(string.digits, k=6))
    return f"ANG-{year}-{month}-{rnd}-01"

def next_offer_version(offer_no: str) -> str:
    """ANG-2026-06-796651-01 → ANG-2026-06-796651-02 (auch ohne Suffix)"""
    parts = offer_no.rsplit('-', 1)
    if len(parts) == 2 and parts[1].isdigit():
        base    = parts[0]
        version = int(parts[1]) + 1
    else:
        base    = offer_no
        version = 2
    return f"{base}-{version:02d}"

def upsert_offer(data: dict):
    if not data.get("id"):
        data["id"] = _new_id()
    data["updated_at"] = datetime.datetime.utcnow().isoformat()
    if USE_SUPABASE:
        payload = {
            "id":            data["id"],
            "offer_no":      data.get("offer_no"),
            "project":       data.get("project"),
            "purchase":      data.get("purchase"),
            "pages":         data.get("pages"),
            "offer_items":   data.get("offer_items"),
            "status":        data.get("status", "draft"),
            "zip_url":       data.get("zip_url", ""),
            "zip_filename":  data.get("zip_filename", ""),
            "zip_downloads": data.get("zip_downloads", 0),
            "zip_expires_at":data.get("zip_expires_at"),
            "pdf_url":       data.get("pdf_url", ""),
            "qr_url":        data.get("qr_url", ""),
            "updated_at":    data["updated_at"],
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

def increment_zip_downloads(offer_id: str):
    """Erhöht den Download-Zähler um 1."""
    if USE_SUPABASE:
        # Aktuellen Wert lesen und erhöhen
        rows = _sb.table("offers").select("zip_downloads").eq("id", offer_id).execute().data
        current = rows[0]["zip_downloads"] if rows else 0
        _sb.table("offers").update({"zip_downloads": current + 1}).eq("id", offer_id).execute()
    else:
        conn = _get_conn()
        conn.execute("UPDATE offers SET zip_downloads = zip_downloads + 1 WHERE id=?", (offer_id,))
        conn.commit(); conn.close()

def archive_expired_offers():
    """Setzt Angebote mit abgelaufenem ZIP auf status='archived'."""
    now = datetime.datetime.utcnow().isoformat()
    if USE_SUPABASE:
        # Alle aktiven Angebote mit abgelaufenem ZIP
        rows = _sb.table("offers").select("id,zip_expires_at").eq("status", "active").execute().data
        for row in rows:
            exp = row.get("zip_expires_at")
            if exp and exp < now:
                _sb.table("offers").update({
                    "status": "archived", "zip_url": "", "zip_filename": ""
                }).eq("id", row["id"]).execute()
    else:
        conn = _get_conn()
        conn.execute(
            """UPDATE offers SET status='archived', zip_url='', zip_filename=''
               WHERE status='active' AND zip_expires_at < ?""", (now,))
        conn.commit(); conn.close()

def list_offers():
    if USE_SUPABASE:
        return _sb.table("offers").select("*").order("created_at", desc=True).execute().data
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM offers ORDER BY created_at DESC").fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        for key in ("project", "purchase", "pages", "offer_items"):
            if isinstance(d.get(key), str):
                try: d[key] = json.loads(d[key])
                except: d[key] = {} if key in ("project", "purchase") else []
        result.append(d)
    return result

def delete_offer(offer_id: str):
    if USE_SUPABASE:
        return _sb.table("offers").delete().eq("id", offer_id).execute()
    conn = _get_conn()
    conn.execute("DELETE FROM offers WHERE id=?", (offer_id,))
    conn.commit(); conn.close()

# ── Einstellungen ─────────────────────────────────────────────────────────────

def get_settings():
    if USE_SUPABASE:
        rows = _sb.table("settings").select("*").eq("key", "pdf_layout").execute().data
        return rows[0]["value"] if rows else {}
    # SQLite Fallback
    try:
        conn = _get_conn()
        row = conn.execute("SELECT value FROM settings WHERE key='pdf_layout'").fetchone()
        conn.close()
        if row:
            return json.loads(row[0]) if isinstance(row[0], str) else row[0]
    except Exception:
        pass
    return {}

def save_settings(data: dict):
    if USE_SUPABASE:
        return _sb.table("settings").upsert({"key": "pdf_layout", "value": data}).execute().data
    conn = _get_conn()
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO settings (key,value) VALUES ('pdf_layout',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (json.dumps(data),))
        conn.commit()
    finally:
        conn.close()
    return data


# ── Vorlagen ──────────────────────────────────────────────────────────────────

def get_templates():
    if USE_SUPABASE:
        return _sb.table("templates").select("*").order("name").execute().data
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM templates ORDER BY name").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        if isinstance(d.get("option_ids"), str):
            try: d["option_ids"] = json.loads(d["option_ids"])
            except: d["option_ids"] = []
        result.append(d)
    return result

def upsert_template(data: dict):
    if not data.get("id"):
        data["id"] = _new_id()
    if USE_SUPABASE:
        return _sb.table("templates").upsert(data).execute().data
    conn = _get_conn()
    conn.execute(
        "INSERT INTO templates (id,name,option_ids) VALUES (:id,:name,:option_ids) "
        "ON CONFLICT(id) DO UPDATE SET name=excluded.name, option_ids=excluded.option_ids",
        {**data, "option_ids": json.dumps(data.get("option_ids", []))}
    )
    conn.commit(); conn.close()
    return data

def delete_template(template_id: str):
    if USE_SUPABASE:
        return _sb.table("templates").delete().eq("id", template_id).execute()
    conn = _get_conn()
    conn.execute("DELETE FROM templates WHERE id=?", (template_id,))
    conn.commit(); conn.close()
