"""
Angebotskonfigurator – FastAPI Backend
Sielaff Austria GmbH
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
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
