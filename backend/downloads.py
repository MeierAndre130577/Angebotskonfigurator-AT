"""
downloads.py – ZIP-Bündelung, signierte Download-Links und automatischer Cleanup

- Erstellt ZIP mit Originaldateien aus Supabase Storage
- Signierte URL (30 Tage)
- Cleanup abgelaufener Dateien
"""

import os, io, uuid, zipfile, datetime, mimetypes, httpx

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SERVICE_KEY  = os.environ.get("SUPABASE_SERVICE_KEY", "")
BUCKET       = "downloads"
EXPIRES_IN   = 30 * 24 * 3600  # 30 Tage in Sekunden
EXPIRES_DAYS = 30


def _supabase_headers(content_type="application/json"):
    return {
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type":  content_type,
    }


def _fetch_file(url: str) -> tuple[bytes, str] | tuple[None, None]:
    """
    Lädt eine Datei von URL herunter.
    Gibt (bytes, original_filename) zurück oder (None, None) bei Fehler.
    """
    if not url:
        return None, None
    try:
        r = httpx.get(url, timeout=30, follow_redirects=True)
        if r.status_code == 200:
            # Original-Dateiname aus Content-Disposition Header
            cd = r.headers.get("content-disposition", "")
            orig_name = ""
            if "filename=" in cd:
                orig_name = cd.split("filename=")[-1].strip().strip('"\'')
            return r.content, orig_name
        print(f"Fetch {url[:60]}... → HTTP {r.status_code}")
    except Exception as e:
        print(f"Fetch failed: {e}")
    return None, None


def _safe_filename(title: str, fallback_ext: str, seen: set) -> str:
    """Erstellt einen sicheren, eindeutigen Dateinamen."""
    safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in title).strip()
    if not safe:
        safe = "Dokument"
    name = f"{safe}.{fallback_ext}"
    if name in seen:
        name = f"{safe}_{uuid.uuid4().hex[:4]}.{fallback_ext}"
    seen.add(name)
    return name


def _ext_from_url(url: str) -> str:
    """Extrahiert die Dateiendung aus einer URL (vor dem ? Token)."""
    path = url.split("?")[0].split("/")[-1]
    if "." in path:
        return path.rsplit(".", 1)[-1].lower()[:5]
    return "pdf"


def cleanup_expired_files():
    """Löscht ZIPs die älter als 30 Tage sind aus Supabase Storage."""
    if not SUPABASE_URL or not SERVICE_KEY:
        return
    try:
        res = httpx.post(
            f"{SUPABASE_URL}/storage/v1/object/list/{BUCKET}",
            headers=_supabase_headers(),
            json={"prefix": "", "limit": 1000},
            timeout=15,
        )
        if res.status_code != 200:
            return

        now     = datetime.datetime.utcnow()
        deleted = 0
        for f in res.json():
            name       = f.get("name", "")
            created_at = f.get("created_at", "")
            if not created_at:
                continue
            try:
                created  = datetime.datetime.fromisoformat(
                    created_at.replace("Z", "+00:00")).replace(tzinfo=None)
                if (now - created).days >= EXPIRES_DAYS:
                    httpx.delete(
                        f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{name}",
                        headers=_supabase_headers(),
                        timeout=10,
                    )
                    deleted += 1
            except Exception:
                continue
        if deleted:
            print(f"Cleanup: {deleted} abgelaufene ZIPs gelöscht")
    except Exception as e:
        print(f"Cleanup failed: {e}")


def create_download_package(
    offer_no: str,
    all_attachments: list,
    pdf_bytes: bytes | None = None,
    pdf_filename: str = "Angebot.pdf",
) -> dict:
    """
    Erstellt ein ZIP mit PDF + allen Anlagendokumenten.
    Gibt dict zurück: {zip_url, zip_filename, expires_at}
    """
    # Zuerst alte Dateien aufräumen
    try:
        cleanup_expired_files()
    except Exception:
        pass

    if not SUPABASE_URL or not SERVICE_KEY:
        return {}

    zip_buf = io.BytesIO()
    seen_names = set()

    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:

        # 1. PDF hinzufügen
        if pdf_bytes:
            zf.writestr(pdf_filename, pdf_bytes)
            seen_names.add(pdf_filename)

        # 2. Alle Anlagendokumente
        for attachment in all_attachments:
            title    = attachment.get("title", "Dokument").strip()
            file_url = attachment.get("file_url", "").strip()

            if not file_url:
                continue

            file_data, orig_name = _fetch_file(file_url)
            if not file_data:
                print(f"Skipping '{title}' – konnte nicht geladen werden")
                continue

            # Extension bestimmen: aus Content-Disposition > URL > Fallback
            if orig_name and "." in orig_name:
                ext = orig_name.rsplit(".", 1)[-1].lower()[:5]
            else:
                ext = _ext_from_url(file_url)

            zip_name = _safe_filename(title, ext, seen_names)
            zf.writestr(zip_name, file_data)
            print(f"ZIP: '{zip_name}' ({len(file_data):,} bytes)")

    zip_bytes = zip_buf.getvalue()
    if len(zip_bytes) < 100:
        print("ZIP leer oder fehlerhaft")
        return {}

    # ZIP hochladen
    zip_filename = f"Angebot_{offer_no}_{uuid.uuid4().hex[:6]}.zip"
    headers_bin  = _supabase_headers("application/zip")
    del headers_bin["Content-Type"]  # httpx setzt es selbst bei binary

    upload_res = httpx.post(
        f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{zip_filename}",
        content=zip_bytes,
        headers={
            "Authorization": f"Bearer {SERVICE_KEY}",
            "Content-Type":  "application/zip",
        },
        timeout=120,
    )
    if upload_res.status_code not in (200, 201):
        print(f"ZIP Upload failed: {upload_res.status_code} {upload_res.text[:200]}")
        return {}

    # Signierte URL
    sign_res = httpx.post(
        f"{SUPABASE_URL}/storage/v1/object/sign/{BUCKET}/{zip_filename}",
        headers=_supabase_headers(),
        json={"expiresIn": EXPIRES_IN},
        timeout=15,
    )
    if sign_res.status_code != 200:
        print(f"Sign failed: {sign_res.status_code}")
        return {}

    signed = sign_res.json().get("signedURL", "")
    if signed.startswith("/"):
        signed = f"{SUPABASE_URL}/storage/v1{signed}"

    expires_at = (
        datetime.datetime.utcnow() + datetime.timedelta(days=EXPIRES_DAYS)
    ).isoformat()

    return {
        "zip_url":      signed,
        "zip_filename": zip_filename,
        "expires_at":   expires_at,
    }


def delete_zip(zip_filename: str) -> bool:
    """Löscht ein ZIP aus Supabase Storage."""
    if not SUPABASE_URL or not SERVICE_KEY or not zip_filename:
        return False
    try:
        res = httpx.delete(
            f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{zip_filename}",
            headers=_supabase_headers(),
            timeout=15,
        )
        return res.status_code in (200, 204)
    except Exception as e:
        print(f"Delete ZIP failed: {e}")
        return False


def generate_qr_code(url: str) -> io.BytesIO | None:
    """Erstellt einen QR-Code als PNG BytesIO."""
    try:
        import qrcode

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
    except Exception as e:
        print(f"QR generation failed: {e}")
        return None
