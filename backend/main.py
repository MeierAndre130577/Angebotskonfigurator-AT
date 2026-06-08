"""
Angebotskonfigurator – FastAPI Backend
Sielaff Austria GmbH
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import os, uuid, httpx
import db
import pdf

app = FastAPI(title="Angebotskonfigurator API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://ak-frontend.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"ok": True, "version": "3.0.0"}

# ── Bild Upload ───────────────────────────────────────────────────────────────

@app.post("/api/upload/image")
async def upload_image(file: UploadFile = File(...)):
    supabase_url = os.environ.get("SUPABASE_URL")
    service_key  = os.environ.get("SUPABASE_SERVICE_KEY")

    ext      = (file.filename or "image.png").split(".")[-1].lower()
    filename = f"{uuid.uuid4()}.{ext}"
    content  = await file.read()

    if not supabase_url or not service_key:
        # Lokal speichern (Entwicklung)
        local_dir = os.path.join(os.path.dirname(__file__), "uploads", "images")
        os.makedirs(local_dir, exist_ok=True)
        with open(os.path.join(local_dir, filename), "wb") as f:
            f.write(content)
        return {"url": f"/uploads/images/{filename}"}

    # Supabase Storage
    upload_url = f"{supabase_url}/storage/v1/object/images/options/{filename}"
    headers = {
        "Authorization": f"Bearer {service_key}",
        "Content-Type": file.content_type or "image/jpeg",
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(upload_url, content=content, headers=headers)

    if res.status_code not in (200, 201):
        return JSONResponse(status_code=500, content={"error": f"Upload fehlgeschlagen: {res.text}"})

    return {"url": f"{supabase_url}/storage/v1/object/public/images/options/{filename}"}

# ── Kunden ────────────────────────────────────────────────────────────────────

class CustomerIn(BaseModel):
    id: Optional[str] = None
    company: str
    contact: Optional[str] = ""
    email: Optional[str] = ""
    billing: Optional[str] = ""
    delivery: Optional[str] = ""

@app.get("/api/customers")
def list_customers():
    return db.get_customers()

@app.post("/api/customers")
def upsert_customer(data: CustomerIn):
    return db.upsert_customer(data.model_dump())

@app.delete("/api/customers/{customer_id}")
def delete_customer(customer_id: str):
    db.delete_customer(customer_id)
    return {"ok": True}

# ── Optionen ──────────────────────────────────────────────────────────────────

class OptionIn(BaseModel):
    id: Optional[str] = None
    cluster: Optional[str] = ""
    name: str
    display_type: Optional[str] = "Ohne Bild + Beschreibung"
    short_text: Optional[str] = ""
    long_text: Optional[str] = ""
    price: Optional[float] = 0
    recurring: Optional[bool] = False
    image_path: Optional[str] = ""
    sort_order: Optional[int] = 0
    documents: Optional[list] = []
    active: Optional[bool] = True

@app.get("/api/options")
def list_options():
    return db.get_options()

@app.post("/api/options")
def upsert_option(data: OptionIn):
    return db.upsert_option(data.model_dump())

@app.delete("/api/options/{option_id}")
def delete_option(option_id: str):
    db.delete_option(option_id)
    return {"ok": True}

# ── Vorlagen ──────────────────────────────────────────────────────────────────

@app.get("/api/templates")
def list_templates():
    return db.get_templates()

@app.post("/api/templates")
def upsert_template(data: dict):
    return db.upsert_template(data)

@app.delete("/api/templates/{template_id}")
def delete_template(template_id: str):
    db.delete_template(template_id)
    return {"ok": True}

# ── Anlagen ───────────────────────────────────────────────────────────────────

class AttachmentIn(BaseModel):
    id: Optional[str] = None
    title: str
    category: Optional[str] = ""
    file_name: Optional[str] = ""
    file_path: Optional[str] = ""
    download_url: Optional[str] = ""
    description: Optional[str] = ""
    internal_note: Optional[str] = ""
    selected_default: Optional[bool] = False
    status: Optional[str] = ""

@app.get("/api/attachments")
def list_attachments():
    return db.get_attachments()

@app.post("/api/attachments")
def upsert_attachment(data: AttachmentIn):
    return db.upsert_attachment(data.model_dump())

@app.delete("/api/attachments/{attachment_id}")
def delete_attachment(attachment_id: str):
    db.delete_attachment(attachment_id)
    return {"ok": True}

# ── Angebote ──────────────────────────────────────────────────────────────────

class OfferIn(BaseModel):
    id: Optional[str] = None
    offer_no: Optional[str] = None
    project: Optional[dict] = {}
    purchase: Optional[dict] = {}
    pages: Optional[list] = []
    offer_items: Optional[list] = []
    status: Optional[str] = "draft"
    zip_url: Optional[str] = ""
    zip_filename: Optional[str] = ""
    zip_downloads: Optional[int] = 0
    zip_expires_at: Optional[str] = None
    pdf_url: Optional[str] = ""
    qr_url: Optional[str] = ""


@app.get("/api/offers")
def list_offers():
    return db.list_offers()

@app.delete("/api/offers/{offer_id}")
def delete_offer(offer_id: str):
    db.delete_offer(offer_id)
    return {"ok": True}

@app.post("/api/offers/{offer_id}/download")
def track_download(offer_id: str):
    """Erhöht Download-Zähler und gibt ZIP-URL zurück."""
    db.increment_zip_downloads(offer_id)
    rows = db.list_offers()
    offer = next((o for o in rows if o["id"] == offer_id), None)
    if not offer:
        raise HTTPException(status_code=404, detail="Angebot nicht gefunden")
    return {"zip_url": offer.get("zip_url", ""), "zip_downloads": offer.get("zip_downloads", 0)}

@app.delete("/api/offers/{offer_id}/zip")
async def delete_offer_zip(offer_id: str):
    """Löscht das ZIP eines Angebots aus Supabase Storage."""
    import downloads as _dl
    rows = db.list_offers()
    offer = next((o for o in rows if o["id"] == offer_id), None)
    if offer and offer.get("zip_filename"):
        _dl.delete_zip(offer["zip_filename"])
        db.upsert_offer({**offer, "zip_url": "", "zip_filename": "", "status": "archived"})
    return {"ok": True}

@app.post("/api/offers/archive-expired")
def archive_expired():
    """Archiviert Angebote mit abgelaufenem ZIP."""
    db.archive_expired_offers()
    return {"ok": True}

@app.post("/api/offers/number")
def generate_offer_number():
    return {"offer_no": db.generate_offer_number()}

@app.post("/api/offers")
def upsert_offer(data: OfferIn):
    return db.upsert_offer(data.model_dump())

@app.get("/api/offers/{offer_no}")
def get_offer(offer_no: str):
    result = db.get_offer_by_number(offer_no)
    if not result:
        raise HTTPException(status_code=404, detail="Angebot nicht gefunden")
    return result

@app.post("/api/offers/generate")
async def generate_full_offer(data: dict):
    """
    Vollständiger Angebots-Workflow:
    1. Angebotsnummer generieren
    2. PDF erstellen (mit QR-Code)
    3. ZIP mit Anhängen erstellen
    4. Angebot in DB speichern
    """
    import downloads as _dl

    project     = data.get("project", {})
    provider    = data.get("provider", {})
    offer_items = data.get("offer_items", [])
    attachments = data.get("attachments", [])

    # 1. Angebotsnummer
    offer_no = db.generate_offer_number()
    project["offerNo"] = offer_no

    # 2. Anlagen sammeln
    s = db.get_settings()
    all_attachments = []
    seen_titles = set()
    for doc in (s.get("mandatory_documents") or []):
        title = doc.get("title","").strip()
        if title and title not in seen_titles:
            seen_titles.add(title); all_attachments.append({**doc, "_mandatory": True})
    for item in offer_items:
        for doc in (item.get("documents") or []):
            title = doc.get("title","").strip()
            if title and title not in seen_titles:
                seen_titles.add(title); all_attachments.append({**doc, "_from_option": item.get("name","")})

    # Cover-Bild, Logo und Website aus Einstellungen in provider einfügen
    if s.get("cover_image"):
        provider = {**provider, "cover_image": s["cover_image"]}
    if s.get("logo_image"):
        provider = {**provider, "logo_image": s["logo_image"]}
    if s.get("website"):
        provider = {**provider, "website": s["website"]}

    # 3. PDF generieren
    pdf_result = pdf.generate_design_pdf({
        "project": project, "provider": provider,
        "offer": offer_items, "attachments": attachments,
        "legal_notice": "", "pages": [], "clusters": [],
    })

    pdf_download_url = pdf_result.get("download_url", "")

    # PDF Bytes direkt aus dem Result – kein Disk-Zugriff nötig
    pdf_bytes = pdf_result.get("pdf_bytes") or b''
    if not pdf_bytes:
        # Fallback: lokal lesen
        local_name = pdf_result.get("local_filename", "")
        if local_name:
            pdf_path = pdf.get_pdf_path(local_name)
            if pdf_path:
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()

    # 4. ZIP erstellen
    pkg = {}
    if all_attachments or pdf_bytes:
        pkg = _dl.create_download_package(
            offer_no        = offer_no,
            all_attachments = all_attachments,
            pdf_bytes       = pdf_bytes,
            pdf_filename    = f"Angebot_{offer_no}.pdf",
        )

    # QR-Code URL speichern (als Data-URL für direkten Zugriff)
    qr_url = pkg.get("zip_url", "")

    # 5. Angebot speichern
    import uuid as _uuid
    offer_data = {
        "id":            str(_uuid.uuid4()),
        "offer_no":      offer_no,
        "project":       project,
        "offer_items":   offer_items,
        "status":        "active",
        "zip_url":       pkg.get("zip_url", ""),
        "zip_filename":  pkg.get("zip_filename", ""),
        "zip_downloads": 0,
        "zip_expires_at":pkg.get("expires_at"),
        "pdf_url":       pdf_download_url,
        "qr_url":        qr_url,
    }
    db.upsert_offer(offer_data)

    # Kunde speichern
    cust = {
        "id":      str(_uuid.uuid4()),
        "company": project.get("customer",""),
        "contact": project.get("contact",""),
        "email":   project.get("customerEmail",""),
        "billing": "", "delivery": "",
    }
    if cust["company"]:
        db.upsert_customer(cust)

    return {
        "ok":          True,
        "offer_no":    offer_no,
        "pdf_url":     pdf_download_url,
        "zip_url":     pkg.get("zip_url",""),
        "zip_filename":pkg.get("zip_filename",""),
        "expires_at":  pkg.get("expires_at",""),
        "qr_url":      qr_url,
    }

@app.post("/api/pdf/preview")
async def preview_pdf(data: dict):
    """Vorschau-PDF ohne Angebotsnummer – nichts wird gespeichert."""
    data_copy = dict(data)
    if "project" in data_copy:
        data_copy["project"] = {**data_copy["project"], "offerNo": "VORSCHAU"}
    result = pdf.generate_design_pdf(data_copy)
    return result

# ── PDF ───────────────────────────────────────────────────────────────────────

class PdfIn(BaseModel):
    project: Optional[dict] = {}
    provider: Optional[dict] = {}
    pages: Optional[list] = []
    offer: Optional[list] = []
    attachments: Optional[list] = []
    legal_notice: Optional[str] = ""
    purchase: Optional[dict] = {}
    clusters: Optional[list] = []

@app.post("/api/pdf/design")
def generate_pdf(data: PdfIn):
    return pdf.generate_design_pdf(data.model_dump())


# ── KI-Übersetzung Endpoint ───────────────────────────────────────────────────

class TranslateIn(BaseModel):
    items: list
    target_language: Optional[str] = "English"

@app.post("/api/translate")
async def translate_offer(data: TranslateIn):
    """Übersetzt Angebots-Texte via Claude API"""
    import json as _json

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY nicht konfiguriert")

    texts = [{"name": i.get("name",""), "short_text": i.get("short_text",""), "long_text": i.get("long_text","")}
             for i in data.items]

    prompt = f"""Translate the following JSON array from German to {data.target_language}.
Translate only the values of "name", "short_text", and "long_text" fields.
Keep all other fields exactly as they are.
Return ONLY valid JSON array, no markdown, no explanation.

{_json.dumps(texts, ensure_ascii=False)}"""

    async with httpx.AsyncClient(timeout=60) as client:
        res = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 4000,
                "messages": [{"role": "user", "content": prompt}]
            }
        )

    if res.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Claude API Fehler: {res.text}")

    result = res.json()
    text   = result["content"][0]["text"]

    # JSON aus Antwort extrahieren
    import re
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if not match:
        raise HTTPException(status_code=500, detail="Ungültige Antwort von Claude")

    translated = _json.loads(match.group())

    # Mit Originalitems zusammenführen
    merged = []
    for i, item in enumerate(data.items):
        merged.append({
            **item,
            "name":       translated[i].get("name",       item.get("name","")),
            "short_text": translated[i].get("short_text", item.get("short_text","")),
            "long_text":  translated[i].get("long_text",  item.get("long_text","")),
        })

    return {"ok": True, "items": merged}

@app.post("/api/upload/document")
async def upload_document(file: UploadFile = File(...)):
    """Dokument (PDF etc.) zu Supabase Storage hochladen"""
    supabase_url = os.environ.get("SUPABASE_URL")
    service_key  = os.environ.get("SUPABASE_SERVICE_KEY")

    ext      = (file.filename or "document.pdf").split(".")[-1].lower()
    filename = f"{uuid.uuid4()}.{ext}"
    content_bytes  = await file.read()

    if not supabase_url or not service_key:
        local_dir = os.path.join(os.path.dirname(__file__), "uploads", "documents")
        os.makedirs(local_dir, exist_ok=True)
        with open(os.path.join(local_dir, filename), "wb") as f:
            f.write(content_bytes)
        return {"url": f"/uploads/documents/{filename}", "filename": filename}

    upload_url = f"{supabase_url}/storage/v1/object/documents/{filename}"
    headers = {
        "Authorization": f"Bearer {service_key}",
        "Content-Type": file.content_type or "application/pdf",
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(upload_url, content=content_bytes, headers=headers)

    if res.status_code not in (200, 201):
        return JSONResponse(status_code=500, content={"error": f"Upload fehlgeschlagen: {res.text}"})

    # Signed URL für Download (1 Jahr gültig)
    signed_url_endpoint = f"{supabase_url}/storage/v1/object/sign/documents/{filename}"
    async with httpx.AsyncClient() as client:
        sign_res = await client.post(signed_url_endpoint,
            headers={"Authorization": f"Bearer {service_key}", "Content-Type": "application/json"},
            json={"expiresIn": 31536000})
    
    if sign_res.status_code == 200:
        signed = sign_res.json().get("signedURL", "")
        url = f"{supabase_url}/storage/v1{signed}" if signed.startswith("/") else signed
    else:
        url = f"{supabase_url}/storage/v1/object/documents/{filename}"

    return {"url": url, "filename": filename}

# ── Einstellungen ─────────────────────────────────────────────────────────────

@app.get("/api/settings")
def get_settings():
    return db.get_settings()

@app.post("/api/settings")
def save_settings(data: dict):
    return db.save_settings(data)


# ── E-Mail ─────────────────────────────────────────────────────────────────────

def _build_email_html(payload: dict) -> str:
    """Erstellt HTML-E-Mail aus Angebotsdaten + gespeicherten Settings."""
    import base64
    import downloads as _dl

    s         = db.get_settings()
    proj      = payload.get('project', {}) or {}

    company    = s.get('company',  'Sielaff Austria GmbH')
    address    = s.get('address',  '')
    phone      = s.get('phone',    '')
    email_addr = s.get('email',    '')
    website    = s.get('website',  '')
    dl_url     = payload.get('download_url', '')

    def rep(tpl):
        return (tpl or '') \
            .replace('{{kunde}}',          proj.get('customer', '')) \
            .replace('{{ansprechpartner}}', proj.get('contact', '') or proj.get('customer', '')) \
            .replace('{{angebotsnummer}}',  proj.get('offerNo', '')) \
            .replace('{{projekt}}',         proj.get('project', '')) \
            .replace('{{datum}}',           proj.get('date', '')) \
            .replace('{{gueltigBis}}',      proj.get('valid', '')) \
            .replace('{{downloadLink}}',    dl_url) \
            .replace('{{anbieter}}',        company)

    body_text = rep(s.get('email_body', ''))
    body_html = ''.join(
        f'<p style="margin:0 0 12px">{ln if ln.strip() else "&nbsp;"}</p>'
        for ln in body_text.split('\n')
    )

    # QR-Code als base64 einbetten
    qr_section = ''
    if dl_url:
        try:
            qr_buf = _dl.generate_qr_code(dl_url)
            if qr_buf:
                qr_b64 = base64.b64encode(qr_buf.getvalue()).decode()
                qr_section = f'''
      <tr>
        <td style="padding:0 32px 28px;text-align:center">
          <img src="data:image/png;base64,{qr_b64}"
               alt="QR-Code" width="150" height="150"
               style="border:1px solid #e0e0e0;border-radius:10px;padding:10px"/>
          <p style="font-size:11px;color:#999;margin:8px 0 0;font-family:Arial,sans-serif">
            QR-Code scannen zum Download aller Dokumente
          </p>
        </td>
      </tr>'''
        except Exception as ex:
            print(f'[email] QR Fehler: {ex}')

    # Download-Button
    dl_btn = ''
    if dl_url:
        dl_btn = f'''
      <tr>
        <td style="padding:0 32px 28px;text-align:center">
          <a href="{dl_url}"
             style="display:inline-block;background:#E30613;color:#ffffff;
                    text-decoration:none;padding:14px 36px;border-radius:8px;
                    font-weight:bold;font-size:15px;font-family:Arial,sans-serif">
            &#128229;&nbsp; Jetzt herunterladen
          </a>
        </td>
      </tr>'''

    # Info-Tabelle
    info_rows = ''
    for label, key in [('Angebotsnummer', 'offerNo'), ('Datum', 'date'),
                       ('Gültig bis', 'valid'), ('Projekt', 'project'), ('Kunde', 'customer')]:
        val = proj.get(key, '')
        if val:
            info_rows += (
                f'<tr><td style="color:#999;padding:6px 10px;width:140px;'
                f'font-family:Arial,sans-serif">{label}</td>'
                f'<td style="padding:6px 10px;font-weight:bold;'
                f'font-family:Arial,sans-serif">{val}</td></tr>'
            )

    info_section = ''
    if info_rows:
        info_section = f'''
      <tr>
        <td style="padding:0 32px 28px">
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="background:#f7f7f7;border-radius:8px;font-size:13px;
                        border-collapse:collapse">
            {info_rows}
          </table>
        </td>
      </tr>'''

    # Footer
    parts = [company]
    if address:    parts.append(address)
    if phone:      parts.append(f'Tel. {phone}')
    if email_addr: parts.append(email_addr)
    if website:    parts.append(website)
    footer_text = ' &nbsp;&middot;&nbsp; '.join(parts)

    RED = '#E30613'

    return f'''<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Angebot</title>
</head>
<body style="margin:0;padding:0;background:#eeeeee;font-family:Arial,Helvetica,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0"
       style="background:#eeeeee;padding:32px 0;border-collapse:collapse">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0"
           style="background:#ffffff;border-radius:12px;overflow:hidden;
                  box-shadow:0 4px 24px rgba(0,0,0,.10);border-collapse:collapse">

      <!-- Header -->
      <tr>
        <td style="background:{RED};padding:28px 32px">
          <span style="font-size:22px;font-weight:bold;color:#ffffff;
                       font-family:Arial,sans-serif;letter-spacing:0.5px">
            {company}
          </span>
        </td>
      </tr>

      <!-- Body -->
      <tr>
        <td style="padding:32px 32px 20px;color:#222222;font-size:14px;
                   line-height:1.7;font-family:Arial,sans-serif">
          {body_html}
        </td>
      </tr>

      {dl_btn}
      {qr_section}
      {info_section}

      <!-- Footer -->
      <tr>
        <td style="background:#f7f7f7;padding:18px 32px;
                   border-top:3px solid {RED};
                   font-size:11px;color:#999999;
                   font-family:Arial,sans-serif;text-align:center">
          {footer_text}
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>'''


@app.post("/api/email/preview")
async def email_preview_endpoint(request: Request):
    from fastapi.responses import HTMLResponse
    payload = await request.json()
    html = _build_email_html(payload)
    return HTMLResponse(content=html)


@app.post("/api/email/send")
async def email_send_endpoint(request: Request):
    import smtplib, ssl
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    payload = await request.json()
    s       = db.get_settings()

    smtp_host = (s.get('smtp_host', '') or '').strip()
    smtp_port = int(s.get('smtp_port', 587) or 587)
    smtp_user = (s.get('smtp_user', '') or '').strip()
    smtp_pass = (s.get('smtp_pass', '') or '').strip()
    from_name = (s.get('smtp_from_name', '') or s.get('company', '') or 'Sielaff Austria').strip()

    if not smtp_host or not smtp_user or not smtp_pass:
        raise HTTPException(status_code=400,
            detail="SMTP nicht konfiguriert. Bitte in Einstellungen → SMTP hinterlegen.")

    to_addr = (payload.get('to', '') or '').strip()
    if not to_addr:
        raise HTTPException(status_code=400,
            detail="Keine Empfänger-E-Mail-Adresse angegeben.")

    proj        = payload.get('project', {}) or {}
    company     = s.get('company', 'Sielaff Austria GmbH')
    subject_tpl = s.get('email_subject', 'Angebot {{angebotsnummer}} für {{kunde}}')
    dl_url      = payload.get('download_url', '')

    def rep(t):
        return (t or '') \
            .replace('{{kunde}}',          proj.get('customer', '')) \
            .replace('{{ansprechpartner}}', proj.get('contact', '') or proj.get('customer', '')) \
            .replace('{{angebotsnummer}}',  proj.get('offerNo', '')) \
            .replace('{{projekt}}',         proj.get('project', '')) \
            .replace('{{datum}}',           proj.get('date', '')) \
            .replace('{{gueltigBis}}',      proj.get('valid', '')) \
            .replace('{{downloadLink}}',    dl_url) \
            .replace('{{anbieter}}',        company)

    subject = rep(subject_tpl)
    html    = _build_email_html(payload)

    msg            = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = f"{from_name} <{smtp_user}>"
    msg['To']      = to_addr
    msg.attach(MIMEText(html, 'html', 'utf-8'))

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as srv:
            srv.ehlo()
            srv.starttls(context=ctx)
            srv.login(smtp_user, smtp_pass)
            srv.send_message(msg)
        return {"ok": True}
    except Exception as ex:
        print(f"[email/send] Fehler: {ex}")
        raise HTTPException(status_code=500,
            detail=f"E-Mail konnte nicht gesendet werden: {ex}")


from fastapi.responses import FileResponse

@app.get("/api/pdf/download/{filename}")
def download_pdf(filename: str):
    import re
    if not re.match(r'^[a-zA-Z0-9_\-\.]+\.pdf$', filename):
        raise HTTPException(status_code=400, detail="Ungültiger Dateiname")
    path = pdf.get_pdf_path(filename)
    if not path:
        raise HTTPException(status_code=404, detail="PDF nicht gefunden")
    return FileResponse(path, media_type='application/pdf', filename=filename)
