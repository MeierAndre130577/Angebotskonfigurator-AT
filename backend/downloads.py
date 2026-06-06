"""
downloads.py – ZIP-Bündelung und signierte Download-Links

Workflow:
1. Alle Dokumente eines Angebots per URL laden
2. Als ZIP bündeln
3. ZIP in Supabase Storage hochladen (Bucket: downloads)
4. Signierte URL mit 30-Tage-Gültigkeit zurückgeben
"""

import os, io, uuid, zipfile, httpx

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SERVICE_KEY  = os.environ.get("SUPABASE_SERVICE_KEY", "")
BUCKET       = "downloads"
EXPIRES_IN   = 30 * 24 * 3600   # 30 Tage in Sekunden


def _fetch_file(url: str) -> bytes | None:
    """Datei von URL laden."""
    if not url:
        return None
    try:
        r = httpx.get(url, timeout=30, follow_redirects=True)
        if r.status_code == 200:
            return r.content
    except Exception as e:
        print(f"Fetch failed for {url}: {e}")
    return None


def _upload_to_supabase(data: bytes, filename: str, content_type: str) -> str | None:
    """Datei in Supabase Storage hochladen und signierte URL zurückgeben."""
    if not SUPABASE_URL or not SERVICE_KEY:
        return None

    headers = {
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type":  content_type,
    }

    # Upload
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{filename}"
    res = httpx.post(upload_url, content=data, headers=headers, timeout=60)
    if res.status_code not in (200, 201):
        print(f"Upload failed: {res.status_code} {res.text}")
        return None

    # Signierte URL generieren
    sign_url = f"{SUPABASE_URL}/storage/v1/object/sign/{BUCKET}/{filename}"
    sign_res = httpx.post(
        sign_url,
        headers={**headers, "Content-Type": "application/json"},
        json={"expiresIn": EXPIRES_IN},
        timeout=15,
    )
    if sign_res.status_code != 200:
        print(f"Sign failed: {sign_res.status_code} {sign_res.text}")
        return None

    signed = sign_res.json().get("signedURL", "")
    if signed.startswith("/"):
        return f"{SUPABASE_URL}/storage/v1{signed}"
    return signed


def create_download_package(
    offer_no: str,
    all_attachments: list,
    pdf_bytes: bytes | None = None,
    pdf_filename: str = "Angebot.pdf",
) -> str | None:
    """
    Erstellt ein ZIP mit allen Dokumenten + optional dem PDF,
    lädt es zu Supabase hoch und gibt die signierte URL zurück.

    all_attachments: Liste von Dicts mit 'title' und 'file_url'
    pdf_bytes:       Fertig generiertes PDF als Bytes (optional)
    """

    zip_buf = io.BytesIO()

    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:

        # PDF hinzufügen
        if pdf_bytes:
            zf.writestr(pdf_filename, pdf_bytes)

        # Alle Anlagendokumente
        seen_names = set()
        for attachment in all_attachments:
            title    = attachment.get("title", "Dokument").strip()
            file_url = attachment.get("file_url", "")
            if not file_url:
                continue

            file_data = _fetch_file(file_url)
            if not file_data:
                continue

            # Dateiname sicher machen
            ext = file_url.split(".")[-1].split("?")[0].lower()
            safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in title)
            filename  = f"{safe_name}.{ext}"

            # Doppelte Namen vermeiden
            if filename in seen_names:
                filename = f"{safe_name}_{uuid.uuid4().hex[:4]}.{ext}"
            seen_names.add(filename)

            zf.writestr(filename, file_data)

    zip_bytes = zip_buf.getvalue()

    if len(zip_bytes) < 100:
        # Leeres oder kaputtes ZIP
        return None

    # ZIP hochladen
    zip_filename = f"Angebot_{offer_no}_{uuid.uuid4().hex[:6]}.zip"
    signed_url   = _upload_to_supabase(zip_bytes, zip_filename, "application/zip")

    return signed_url


def generate_qr_code(url: str, size_mm: float = 35) -> io.BytesIO | None:
    """
    Erstellt einen QR-Code als PNG BytesIO.
    size_mm: gewünschte Größe in mm (wird in Pixel umgerechnet)
    """
    try:
        import qrcode
        from qrcode.image.pure import PyPNGImage

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf

    except ImportError:
        print("qrcode not installed")
        return None
    except Exception as e:
        print(f"QR generation failed: {e}")
        return None
