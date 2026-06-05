"""
PDF-Generierung – ReportLab
Platzhalter für den Prototyp; die vollständige Logik kommt aus dem v2-Backend.
"""

import os
import uuid
import datetime

EXPORT_DIR = os.path.join(os.path.dirname(__file__), "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)


def generate_design_pdf(data: dict) -> dict:
    """
    Erzeugt ein einfaches Design-PDF und gibt die Download-URL zurück.
    In der Produktion wird hier ReportLab / Supabase Storage verwendet.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        project  = data.get("project") or {}
        provider = data.get("provider") or {}
        offer    = data.get("offer")    or []

        filename  = f"Angebot_{project.get('offerNo','ENTWURF')}_{uuid.uuid4().hex[:6]}.pdf"
        filepath  = os.path.join(EXPORT_DIR, filename)

        c = canvas.Canvas(filepath, pagesize=A4)
        w, h = A4

        # Header
        c.setFillColorRGB(0.89, 0.02, 0.07)  # Sielaff-Rot
        c.rect(0, h - 60, w, 60, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(30, h - 38, provider.get("company", "Sielaff Austria GmbH"))

        # Angebotsnummer
        c.setFillColorRGB(0.1, 0.1, 0.1)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(30, h - 90, f"Angebot {project.get('offerNo', '—')}")
        c.setFont("Helvetica", 10)
        c.drawString(30, h - 110, f"Datum: {project.get('date', '')}  ·  Gültig bis: {project.get('valid', '')}")
        c.drawString(30, h - 130, f"Kunde: {project.get('customer', '')}  ·  {project.get('contact', '')}")

        # Positionen
        y = h - 180
        c.setFont("Helvetica-Bold", 11)
        c.drawString(30, y, "Positionen")
        y -= 20
        c.setFont("Helvetica", 10)
        for item in offer[:20]:
            price = item.get("price", 0)
            label = f"{'[optional] ' if item.get('optional') else ''}{item.get('name','')}"
            price_str = f"{'inkl.' if price == 0 else (str(price) + ' €/Mo.' if item.get('recurring') else str(price) + ' €')}"
            c.drawString(40, y, f"• {label}")
            c.drawRightString(w - 30, y, price_str)
            y -= 16
            if y < 60:
                c.showPage()
                y = h - 60

        c.save()
        return {"ok": True, "download_url": f"/api/pdf/download/{filename}"}

    except ImportError:
        # ReportLab nicht installiert – gibt Dummy zurück
        return {"ok": False, "error": "ReportLab nicht installiert (pip install reportlab)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_pdf_path(filename: str) -> str | None:
    path = os.path.join(EXPORT_DIR, filename)
    return path if os.path.exists(path) else None
