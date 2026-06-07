"""
PDF-Generierung – Angebotskonfigurator Sielaff Austria v5
- Deckblatt: komplett weißes Design
- Kopfzeile: topMargin korrekt
- Summe in Angebotsübersicht
- Anlagen aus Optionsdokumenten (dedupliziert)
"""

import os, uuid, io, httpx
import downloads as _dl
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, PageBreak, Image as RLImage, KeepTogether)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

RED   = colors.HexColor('#E30613')
DARK  = colors.HexColor('#1D1D1B')
MUTED = colors.HexColor('#71717a')
LINE  = colors.HexColor('#e4e4e7')
WHITE = colors.white
BG    = colors.HexColor('#f8f8f8')

W, H       = A4
# Defaults – werden durch DB-Einstellungen überschrieben
HEADER_H   = 26*mm
MARGIN_L   = 20*mm
MARGIN_R   = 12*mm
MARGIN_T   = HEADER_H + 13*mm
MARGIN_B   = 22*mm

def _get_pdf_settings():
    """Lädt PDF-Einstellungen aus der DB, fällt auf Defaults zurück"""
    try:
        import db as _db
        s = _db.get_settings()
        if not s: return {}
        print(f"[settings] cover_image={s.get('cover_image','')!r}  logo_image={s.get('logo_image','')!r}")
        return s
    except Exception as e:
        print(f"[settings] Fehler beim Laden: {e}")
        return {}

EXPORT_DIR = os.path.join(os.path.dirname(__file__), 'exports')
os.makedirs(EXPORT_DIR, exist_ok=True)
LOGO_PATH  = os.path.join(os.path.dirname(__file__), 'Logo_Sielaff.png')

def money(n):
    try:
        return f"€ {float(n):,.2f}".replace(',','X').replace('.', ',').replace('X','.')
    except:
        return "€ 0,00"

def fetch_image(url: str) -> io.BytesIO | None:
    if not url:
        return None

    print(f"[fetch_image] URL: {url!r}")

    # ── Lokale Uploads (/uploads/...) ─────────────────────────────────────────
    if url.startswith('/uploads/'):
        local_path = os.path.join(
            os.path.dirname(__file__),
            url.lstrip('/').replace('/', os.sep)
        )
        print(f"[fetch_image] lokaler Pfad: {local_path!r}, existiert: {os.path.exists(local_path)}")
        if os.path.exists(local_path):
            with open(local_path, 'rb') as f:
                return io.BytesIO(f.read())
        return None

    # ── Remote URL (Supabase oder extern) ─────────────────────────────────────
    try:
        headers = {}
        # Supabase-URLs ggf. mit Service-Key authentifizieren
        supabase_url = os.environ.get('SUPABASE_URL', '')
        service_key  = os.environ.get('SUPABASE_SERVICE_KEY', '')
        if supabase_url and service_key and supabase_url in url:
            headers['Authorization'] = f'Bearer {service_key}'

        r = httpx.get(url, timeout=15, follow_redirects=True, headers=headers)
        print(f"[fetch_image] HTTP {r.status_code} für {url!r}")
        if r.status_code == 200:
            return io.BytesIO(r.content)
        else:
            print(f"[fetch_image] Fehler-Body: {r.text[:200]}")
    except Exception as e:
        print(f"[fetch_image] Exception: {e}")

    return None

def make_image(img_data: io.BytesIO, max_w: float, max_h: float) -> RLImage | None:
    """
    Erstellt ein RLImage das NIEMALS skaliert wird (preserveAspectRatio).
    Bild wird nur verkleinert wenn es größer als max_w/max_h ist,
    nie vergrößert. Originalauflösung bleibt erhalten.
    """
    if not img_data:
        return None
    try:
        img_data.seek(0)
        from PIL import Image as PILImage
        pil = PILImage.open(img_data)
        orig_w_px, orig_h_px = pil.size
        dpi = 96  # Standard-Bildschirm DPI
        orig_w_pt = orig_w_px / dpi * 72   # px → pt
        orig_h_pt = orig_h_px / dpi * 72

        # Nur verkleinern, nie vergrößern
        scale = min(1.0, max_w / orig_w_pt, max_h / orig_h_pt)
        final_w = orig_w_pt * scale
        final_h = orig_h_pt * scale

        img_data.seek(0)
        return RLImage(img_data, width=final_w, height=final_h)
    except Exception:
        # PIL nicht verfügbar – Fallback mit max_w/max_h aber preserveAspectRatio
        try:
            img_data.seek(0)
            img = RLImage(img_data, width=max_w, height=max_h)
            img.preserveAspectRatio = True
            return img
        except Exception:
            return None

# ── Icon-Zeichner für Info-Box ────────────────────────────────────────────────

def _draw_icon(c: canvas.Canvas, cx: float, cy: float, kind: str):
    """
    Zeichnet ein einfaches Linien-Icon zentriert bei (cx, cy).
    kind: 'doc' | 'cal' | 'person' | 'brief' | 'clock' | 'layers'
    """
    c.setStrokeColor(colors.HexColor('#888888'))
    c.setFillColor(colors.HexColor('#888888'))
    c.setLineWidth(0.9)
    r = 5  # halbe Icon-Größe in pt

    if kind == 'doc':
        # Dokument: Rechteck mit Ecke + Linien
        c.rect(cx - r + 1, cy - r, r * 2 - 2, r * 2, fill=0, stroke=1)
        for dy in (2, -1, -4):
            c.line(cx - r + 3, cy + dy, cx + r - 2, cy + dy)

    elif kind == 'cal':
        # Kalender: Rechteck + Gitterlinien + Bügelchen
        c.rect(cx - r, cy - r, r * 2, r * 2, fill=0, stroke=1)
        c.line(cx - r, cy + 1, cx + r, cy + 1)          # horizontale Trennlinie
        c.line(cx - 2, cy + r, cx - 2, cy + r + 3)       # linker Bügel
        c.line(cx + 2, cy + r, cx + 2, cy + r + 3)       # rechter Bügel

    elif kind == 'person':
        # Person: Kreis (Kopf) + Halbbogen (Körper)
        c.circle(cx, cy + 2, 3.0, fill=0, stroke=1)
        p = c.beginPath()
        p.moveTo(cx - r, cy - r)
        p.curveTo(cx - r, cy - 1, cx + r, cy - 1, cx + r, cy - r)
        c.drawPath(p, fill=0, stroke=1)

    elif kind == 'brief':
        # Aktentasche: Rechteck + Griff oben mittig
        c.rect(cx - r, cy - r, r * 2, r * 2 - 1, fill=0, stroke=1)
        c.rect(cx - 3, cy + r - 3, 6, 3, fill=0, stroke=1)   # Griff
        c.line(cx - r, cy, cx + r, cy)                         # mittlere Linie

    elif kind == 'clock':
        # Uhr: Kreis + Zeiger
        c.circle(cx, cy, r + 0.5, fill=0, stroke=1)
        c.line(cx, cy, cx, cy + r - 1)       # Stundenzeiger (oben)
        c.line(cx, cy, cx + r - 1, cy)       # Minutenzeiger (rechts)

    elif kind == 'layers':
        # Ebenen: drei versetzte Rechtecke
        for k, dy in enumerate((-3, 0, 3)):
            off = abs(dy)
            c.rect(cx - r + off, cy + dy - 1, (r - off) * 2, 2, fill=1, stroke=0)


# ── Deckblatt – Neues Design ──────────────────────────────────────────────────

def draw_cover(c: canvas.Canvas, data: dict):
    """
    Deckblatt Variante B – Eleganter Bogen:
    - Bild rechts, hinter einer geschwungenen Bézier-Kurve
    - Weiße Bezier-Maske (kein clipPath) deckt linken Bereich ab
    - Logo + ANGEBOT oben links, Info-Box unten links verankert
    - ARCH_CP_X = 378pt  >  ANGEBOT-Ende ~338pt  → kein Überlauf
    """
    from PIL import Image as PILImage

    project  = data.get('project')  or {}
    provider = data.get('provider') or {}

    C_RED       = colors.HexColor('#E30613')
    C_DARK      = colors.HexColor('#1D1D1B')
    C_GRAY_DARK = colors.HexColor('#555555')
    C_GRAY_LINE = colors.HexColor('#E0E0E0')
    C_ICON_BG   = colors.HexColor('#F2F2F2')
    C_FOOTER_BG = colors.HexColor('#E2E2E2')

    FOOTER_H = 88

    # Bogen-Parameter (sorgfältig berechnet, kein Overlap mit Text)
    ARCH_TOP_X = W * 0.700   # 416pt – Bogenbeginn oben rechts
    ARCH_CP_X  = W * 0.635   # 378pt – linkster Punkt der Kurve (40pt Abstand zu ANGEBOT-Ende ~338pt)
    ARCH_BOT_X = W * 0.770   # 458pt – Bogenende unten rechts
    ARCH_CP1_Y = H * 0.650   # 547pt – oberer Kontrollpunkt
    ARCH_CP2_Y = H * 0.350   # 295pt – unterer Kontrollpunkt

    # Bild-Zielbereich: ab ARCH_CP_X (linkster Bogenpunkt)
    IMG_X = ARCH_CP_X         # 378pt
    IMG_Y = FOOTER_H          # 88pt
    IMG_W = W - ARCH_CP_X     # 217pt
    IMG_H = H - FOOTER_H      # 754pt

    # ── 1. Weißer Seitenhintergrund ───────────────────────────────────────────
    c.setFillColor(colors.white)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # ── 2. Cover-Bild (PIL-Zuschnitt auf exaktes Seitenverhältnis) ───────────
    cover_url = (provider.get('cover_image') or
                 project.get('coverImage')   or
                 data.get('cover_image')     or '')
    cover_img = fetch_image(cover_url) if cover_url else None

    c.saveState()
    if cover_img:
        try:
            cover_img.seek(0)
            raw = cover_img.read()
            pil = PILImage.open(io.BytesIO(raw))
            if pil.mode in ('RGBA', 'LA', 'P'):
                bg = PILImage.new('RGB', pil.size, (255, 255, 255))
                src = pil.convert('RGBA') if pil.mode == 'P' else pil
                bg.paste(src, mask=src.split()[-1])
                pil = bg
            elif pil.mode != 'RGB':
                pil = pil.convert('RGB')
            pw, ph = pil.size
            ratio = IMG_W / IMG_H
            if (pw / ph) > ratio:
                nw = int(ph * ratio)
                pil = pil.crop(((pw - nw) // 2, 0, (pw + nw) // 2, ph))
            else:
                nh = int(pw / ratio)
                pil = pil.crop((0, (ph - nh) // 2, pw, (ph + nh) // 2))
            buf = io.BytesIO()
            pil.save(buf, 'JPEG', quality=88)
            buf.seek(0)
            c.drawImage(ImageReader(buf), IMG_X, IMG_Y, width=IMG_W, height=IMG_H)
            print(f'[draw_cover] Bild: {IMG_W:.0f}x{IMG_H:.0f}pt @ ({IMG_X:.0f},{IMG_Y:.0f})')
        except Exception as e:
            print(f'[draw_cover] Bild-Fehler: {e}')
            c.setFillColor(colors.HexColor('#CCCCCC'))
            c.rect(IMG_X, IMG_Y, IMG_W, IMG_H, fill=1, stroke=0)
    else:
        c.setFillColor(colors.HexColor('#CCCCCC'))
        c.rect(IMG_X, IMG_Y, IMG_W, IMG_H, fill=1, stroke=0)

    # ── 3. Weiße Bogen-Maske (linker Bereich, über dem Bild) ─────────────────
    c.setFillColor(colors.white)
    p_mask = c.beginPath()
    p_mask.moveTo(0, H)
    p_mask.lineTo(ARCH_TOP_X, H)
    p_mask.curveTo(ARCH_CP_X, ARCH_CP1_Y,
                   ARCH_CP_X, ARCH_CP2_Y,
                   ARCH_BOT_X, FOOTER_H)
    p_mask.lineTo(0, FOOTER_H)
    p_mask.close()
    c.drawPath(p_mask, fill=1, stroke=0)

    c.restoreState()  # Farbzustand sauber zurücksetzen

    # ── 4. Weißer Bogenstrich (schärft die Bildkante) ─────────────────────────
    c.setStrokeColor(colors.white)
    c.setLineWidth(4)
    p_border = c.beginPath()
    p_border.moveTo(ARCH_TOP_X, H)
    p_border.curveTo(ARCH_CP_X, ARCH_CP1_Y,
                     ARCH_CP_X, ARCH_CP2_Y,
                     ARCH_BOT_X, FOOTER_H)
    c.drawPath(p_border, fill=0, stroke=1)

    # ── 5. Logo oben links ────────────────────────────────────────────────────
    c.saveState()
    LOGO_X   = 35
    LOGO_MAX = 56
    LOGO_Y   = H - LOGO_MAX - 40

    logo_url = provider.get('logo_image') or ''
    logo_img = fetch_image(logo_url) if logo_url else None

    if logo_img:
        try:
            logo_img.seek(0)
            lb = logo_img.read()
            pil_l = PILImage.open(io.BytesIO(lb))
            lw, lh = pil_l.size
            sc = min(1.0, LOGO_MAX / (lw / 96 * 72), LOGO_MAX / (lh / 96 * 72))
            fw = lw / 96 * 72 * sc
            fh = lh / 96 * 72 * sc
            c.drawImage(ImageReader(io.BytesIO(lb)),
                        LOGO_X, LOGO_Y + (LOGO_MAX - fh) / 2,
                        width=fw, height=fh,
                        preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f'[draw_cover] Logo-Fehler: {e}')
            c.setFillColor(C_RED)
            c.rect(LOGO_X, LOGO_Y, LOGO_MAX, LOGO_MAX, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont('Helvetica-Bold', 10)
            c.drawCentredString(LOGO_X + LOGO_MAX / 2, LOGO_Y + LOGO_MAX / 2 - 3, 'LOGO')
    else:
        c.setFillColor(C_RED)
        c.rect(LOGO_X, LOGO_Y, LOGO_MAX, LOGO_MAX, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont('Helvetica-Bold', 10)
        c.drawCentredString(LOGO_X + LOGO_MAX / 2, LOGO_Y + LOGO_MAX / 2 - 3, 'LOGO')
    c.restoreState()

    # ── 6. ANGEBOT + Untertitel (oben links, unter Logo) ─────────────────────
    # Times-Roman 62pt → Breite ≈ 303pt → endet bei x≈338pt < ARCH_CP_X=378pt ✓
    c.setFillColor(C_DARK)
    c.setFont('Times-Roman', 62)
    c.drawString(35, H - 185, 'ANGEBOT')

    c.setStrokeColor(C_RED)
    c.setLineWidth(2.5)
    c.line(35, H - 202, 93, H - 202)

    c.setFont('Helvetica', 12)
    c.setFillColor(C_DARK)
    c.drawString(35, H - 226, 'Maßgeschneiderte Lösung für Ihr Vorhaben')

    # ── 7. Info-Box (am unteren Rand der linken Spalte verankert) ────────────
    BOX_X = 35
    BOX_W = 350   # endet bei ~385pt, liegt sicher im weißen Bereich
    ROW_H = 36
    rows = [
        ('doc',    'Angebotsnummer', project.get('offerNo',   '')),
        ('cal',    'Datum',          project.get('date',       '')),
        ('person', 'Kunde',          project.get('customer',   '')),
        ('brief',  'Projekt',        project.get('project',    '')),
        ('person', 'Ansprechpartner',project.get('contact',    '')),
        ('clock',  'Gültig bis',     project.get('valid',      '')),
        ('layers', 'Version',        project.get('version',    '1.0')),
    ]
    BOX_H = ROW_H * len(rows) + 16   # = 268pt
    BOX_Y = FOOTER_H + 35            # 35pt über der Fußzeile

    # Schatten
    c.setFillColor(colors.HexColor('#DADADA'))
    c.roundRect(BOX_X + 4, BOX_Y - 5, BOX_W, BOX_H, 8, fill=1, stroke=0)
    # Weißer Kasten
    c.setFillColor(colors.white)
    c.roundRect(BOX_X, BOX_Y, BOX_W, BOX_H, 8, fill=1, stroke=0)

    for i, (icon_kind, label, value) in enumerate(rows):
        row_cy = BOX_Y + BOX_H - 8 - (i + 1) * ROW_H + ROW_H * 0.5
        ICON_CX = BOX_X + 20

        c.setFillColor(C_ICON_BG)
        c.circle(ICON_CX, row_cy, 9, fill=1, stroke=0)
        _draw_icon(c, ICON_CX, row_cy, icon_kind)

        c.setFont('Helvetica-Bold', 9)
        c.setFillColor(colors.black)
        c.drawString(BOX_X + 38, row_cy - 3, label)

        c.setFont('Helvetica', 9)
        c.setFillColor(colors.black)
        c.drawString(BOX_X + 158, row_cy - 3, str(value)[:45])

        if i < len(rows) - 1:
            sep_y = BOX_Y + BOX_H - 8 - (i + 1) * ROW_H
            c.setStrokeColor(C_GRAY_LINE)
            c.setLineWidth(0.4)
            c.line(BOX_X + 12, sep_y, BOX_X + BOX_W - 12, sep_y)

    # ── Fußzeile (wird als letztes gezeichnet → liegt garantiert oben) ───────
    c.setFillColor(C_FOOTER_BG)
    c.rect(0, 0, W, FOOTER_H, fill=1, stroke=0)
    # Trennlinie oben
    c.setStrokeColor(colors.HexColor('#CCCCCC'))
    c.setLineWidth(0.5)
    c.line(0, FOOTER_H, W, FOOTER_H)

    # Vertikale Trenner
    c.setStrokeColor(colors.HexColor('#BBBBBB'))
    c.setLineWidth(0.5)
    c.line(75, 14, 75, FOOTER_H - 14)
    sep2_x = W * 0.51
    c.line(sep2_x, 14, sep2_x, FOOTER_H - 14)

    # Gebäude-Icon (einfache Linien)
    bx, by = 22, FOOTER_H - 62
    c.setStrokeColor(colors.HexColor('#888888'))
    c.setLineWidth(1)
    c.rect(bx, by, 30, 40, fill=0, stroke=1)
    c.rect(bx + 10, by, 10, 15, fill=0, stroke=1)
    c.line(bx + 4, by + 26, bx + 10, by + 26)
    c.line(bx + 20, by + 26, bx + 26, by + 26)

    # Firmendaten (linke Spalte)
    c.setFont('Helvetica-Bold', 8)
    c.setFillColor(C_DARK)
    c.drawString(84, FOOTER_H - 22, provider.get('company', ''))
    c.setFont('Helvetica', 7.5)
    c.setFillColor(C_GRAY_DARK)
    addr = provider.get('address', '')
    # Adresse ggf. auf zwei Zeilen aufteilen
    if ',' in addr:
        parts = addr.split(',', 1)
        c.drawString(84, FOOTER_H - 34, parts[0].strip() + ',')
        c.drawString(84, FOOTER_H - 46, parts[1].strip())
    else:
        c.drawString(84, FOOTER_H - 34, addr)

    # Kontakt (mittlere Spalte)
    col2_x = sep2_x + 12
    c.setFont('Helvetica', 7.5)
    c.setFillColor(C_GRAY_DARK)
    c.drawString(col2_x, FOOTER_H - 22, provider.get('phone',   ''))
    c.drawString(col2_x, FOOTER_H - 34, provider.get('email',   ''))
    c.drawString(col2_x, FOOTER_H - 46, provider.get('website', ''))

    # Slogan rechts
    slogan = 'Kompetent. Klar. Verlässlich.'
    c.setFont('Helvetica-Bold', 9)
    c.setFillColor(C_DARK)
    c.drawRightString(W - 25, FOOTER_H - 28, slogan)
    # Rote Linie unter Slogan
    slogan_w = c.stringWidth(slogan, 'Helvetica-Bold', 9)
    c.setStrokeColor(C_RED)
    c.setLineWidth(1.5)
    c.line(W - 25 - slogan_w, FOOTER_H - 35, W - 25, FOOTER_H - 35)

    c.showPage()


# ── Kopf- und Fußzeile Canvas ─────────────────────────────────────────────────

def make_canvas_class(project, provider, HEADER_H=None, MARGIN_L=None, MARGIN_R=None, f_d=None):
    if HEADER_H is None: HEADER_H = 26*mm
    if MARGIN_L is None: MARGIN_L = 20*mm
    if MARGIN_R is None: MARGIN_R = 12*mm
    if f_d     is None: f_d      = 14*mm
    class MyCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._page_num = 1

        def showPage(self):
            self._draw_hf()
            self._page_num += 1
            super().showPage()

        def save(self):
            self._draw_hf()
            super().save()

        def _draw_hf(self):
            c = self

            # Roter Seitenstreifen links
            c.setFillColor(RED)
            c.rect(0, 0, 5*mm, H, fill=1, stroke=0)

            # Kopfzeile – weißer Hintergrund oben
            c.setFillColor(WHITE)
            c.rect(5*mm, H - HEADER_H, W - 5*mm, HEADER_H, fill=1, stroke=0)

            # Trennlinie unter Kopfzeile
            c.setStrokeColor(LINE)
            c.setLineWidth(0.5)
            c.line(MARGIN_L, H - HEADER_H, W - MARGIN_R, H - HEADER_H)

            # Logo + Text vertikal mittig in der Kopfzeile
            logo_size  = 14*mm
            header_mid = H - HEADER_H + HEADER_H / 2   # vertikale Mitte der Kopfzeile
            logo_y     = header_mid - logo_size / 2      # Logo zentriert auf Mitte
            text_y     = header_mid - 2.5*mm             # Text auf gleicher Höhe wie Logo-Mitte

            if os.path.exists(LOGO_PATH):
                try:
                    c.drawImage(LOGO_PATH,
                               MARGIN_L,
                               logo_y,
                               width=logo_size, height=logo_size,
                               preserveAspectRatio=True, mask='auto')
                except Exception:
                    pass

            # Firmenname – vertikal mittig neben Logo
            c.setFillColor(DARK)
            c.setFont('Helvetica-Bold', 8)
            c.drawString(MARGIN_L + logo_size + 3*mm, text_y,
                        provider.get('company', 'Sielaff Austria GmbH'))

            # Angebotsnummer Mitte – gleiche Höhe
            c.setFont('Helvetica', 7.5)
            c.setFillColor(MUTED)
            offer_no = project.get('offerNo', '')
            c.drawCentredString(W/2, text_y,
                               f'Angebot {offer_no}' if offer_no else '')

            # Datum rechts – gleiche Höhe
            c.drawRightString(W - MARGIN_R, text_y,
                             project.get('date', ''))

            # Fußzeile
            c.setStrokeColor(LINE)
            c.line(MARGIN_L, f_d, W - MARGIN_R, f_d)
            addr = (f"{provider.get('company','')}  ·  {provider.get('address','')}  ·  "
                    f"{provider.get('email','')}  ·  {provider.get('phone','')}")
            c.setFont('Helvetica', 6.5)
            c.setFillColor(MUTED)
            c.drawString(MARGIN_L, f_d - 6*mm, addr)
            c.drawRightString(W - MARGIN_R, f_d - 6*mm,
                             f'Seite {self._page_num + 1}')

    return MyCanvas

# ── Styles ────────────────────────────────────────────────────────────────────

def get_styles():
    return {
        'h1':   ParagraphStyle('h1',   fontName='Helvetica-Bold', fontSize=20, textColor=DARK, spaceAfter=4),
        'h2':   ParagraphStyle('h2',   fontName='Helvetica-Bold', fontSize=13, textColor=DARK, spaceAfter=3),
        'h3':   ParagraphStyle('h3',   fontName='Helvetica-Bold', fontSize=10, textColor=DARK, spaceAfter=2),
        'body': ParagraphStyle('body', fontName='Helvetica',      fontSize=9,  textColor=DARK, spaceAfter=3, leading=13),
        'muted':ParagraphStyle('muted',fontName='Helvetica',      fontSize=7.5,textColor=MUTED,spaceAfter=2),
        'price':ParagraphStyle('price',fontName='Helvetica-Bold', fontSize=10, textColor=RED,  alignment=TA_RIGHT),
        'toc':  ParagraphStyle('toc',  fontName='Helvetica',      fontSize=10, textColor=DARK, spaceAfter=5),
        'tocn': ParagraphStyle('tocn', fontName='Helvetica-Bold', fontSize=10, textColor=RED,  spaceAfter=5),
    }

def section_title(story, text, S, CW):
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(text, S['h1']))
    story.append(Table([['']], colWidths=[CW],
        style=[('LINEBELOW',(0,0),(-1,-1),1.5,RED),
               ('TOPPADDING',(0,0),(-1,-1),0),
               ('BOTTOMPADDING',(0,0),(-1,-1),2)]))
    story.append(Spacer(1, 3*mm))

# ── Haupt-Generator ───────────────────────────────────────────────────────────

def generate_design_pdf(data: dict) -> dict:
    project     = data.get('project')      or {}
    provider    = data.get('provider')     or {}
    offer       = data.get('offer')        or []
    attachments = data.get('attachments')  or []
    legal       = data.get('legal_notice') or ''

    # Einstellungen aus DB laden
    s = _get_pdf_settings()
    h_h  = s.get('header_height_mm',  26) * mm
    m_t  = s.get('margin_top_mm',     39) * mm
    m_b  = s.get('margin_bottom_mm',  22) * mm
    m_l  = s.get('margin_left_mm',    20) * mm
    m_r  = s.get('margin_right_mm',   12) * mm
    f_d  = s.get('footer_distance_mm',14) * mm
    # Provider aus Einstellungen überschreiben falls vorhanden
    if s.get('company'): provider = {**provider,
        'company': s.get('company', provider.get('company','')),
        'address': s.get('address', provider.get('address','')),
        'email':   s.get('email',   provider.get('email','')),
        'phone':   s.get('phone',   provider.get('phone','')),
        'website': s.get('website', provider.get('website','')),
    }
    if s.get('legal_notice') and not legal:
        legal = s['legal_notice']

    filename = f"Angebot_{project.get('offerNo','ENTWURF')}_{uuid.uuid4().hex[:6]}.pdf"
    filepath = os.path.join(EXPORT_DIR, filename)

    # ── Anlagen sammeln: Pflichtanlagen + Optionsdokumente + explizite Anlagen ─
    all_attachments = []
    seen_titles = set()

    # 1. Pflichtanlagen aus Einstellungen (immer zuerst)
    for doc in (s.get('mandatory_documents') or []):
        title = doc.get('title', '').strip()
        if title and title not in seen_titles:
            seen_titles.add(title)
            all_attachments.append({**doc, '_mandatory': True})

    # 2. Dokumente aus Optionen
    for item in offer:
        for doc in (item.get('documents') or []):
            title = doc.get('title', '').strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                all_attachments.append({**doc, '_from_option': item.get('name','')})

    # 3. Explizite Anlagen
    for a in attachments:
        if not (a.get('selected') or a.get('selected_default')):
            continue
        title = a.get('title', '').strip()
        if title and title not in seen_titles:
            seen_titles.add(title)
            all_attachments.append(a)

    # ── Deckblatt ─────────────────────────────────────────────────────────────
    # Cover-Foto und Logo aus Einstellungen einfügen
    if s.get('cover_image'):
        provider = {**provider, 'cover_image': s['cover_image']}
    if s.get('logo_image'):
        provider = {**provider, 'logo_image': s['logo_image']}
    cover_buf = io.BytesIO()
    c_cover   = canvas.Canvas(cover_buf, pagesize=A4)
    draw_cover(c_cover, {**data, 'provider': provider})
    c_cover.save()
    cover_buf.seek(0)

    # ── Inhalt ────────────────────────────────────────────────────────────────
    content_buf = io.BytesIO()
    MyCanvas    = make_canvas_class(project, provider, h_h, m_l, m_r, f_d)

    doc = SimpleDocTemplate(
        content_buf, pagesize=A4,
        leftMargin=m_l, rightMargin=m_r,
        topMargin=m_t,  bottomMargin=m_b,
    )

    S   = get_styles()
    CW  = W - m_l - m_r
    story = []

    # Inhaltsverzeichnis
    section_title(story, 'Inhaltsverzeichnis', S, CW)
    for num, label in [('1','Angebotsübersicht'),('2','Detailbeschreibungen'),
                       ('3','Preiszusammenfassung'),('4','Anlagen'),('5','Rechtliche Hinweise')]:
        t = Table([[Paragraph(f'{num}.', S['tocn']), Paragraph(label, S['toc'])]],
                  colWidths=[10*mm, CW-10*mm])
        t.setStyle(TableStyle([
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('LINEBELOW',(0,0),(-1,-1),0.3,LINE),
            ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ]))
        story.append(t)
    story.append(PageBreak())

    # ── Angebotsübersicht ─────────────────────────────────────────────────────
    section_title(story, '1. Angebotsübersicht', S, CW)
    story.append(Paragraph(
        f"Kunde: <b>{project.get('customer','')}</b>  ·  "
        f"Projekt: <b>{project.get('project','')}</b>  ·  "
        f"Angebot: <b>{project.get('offerNo','')}</b>  ·  "
        f"Datum: <b>{project.get('date','')}</b>", S['body']))
    story.append(Spacer(1, 3*mm))

    one_time = sum((i.get('original_price') or i.get('price') or 0) for i in offer if not i.get('recurring') and not i.get('optional'))
    monthly  = sum((i.get('original_price') or i.get('price') or 0) for i in offer if i.get('recurring') and not i.get('optional'))

    hdr  = [Paragraph(f'<b>{x}</b>', S['muted']) for x in ['#','Option','Cluster','Preis']]
    rows = [hdr]
    for i, item in enumerate(offer, 1):
        p          = item.get('original_price') or item.get('price') or 0
        is_opt     = item.get('optional', False)
        if is_opt:
            price_str = money(p) + ('/Mo.' if item.get('recurring') else '')
            ps = f'optional ({price_str})'
            name_text = f"{item.get('name','')}  <font color='#71717a' size='7'>[optional]</font>"
        else:
            ps = 'inklusive' if p==0 else (money(p)+'/Mo.' if item.get('recurring') else money(p))
            name_text = item.get('name','')
        rows.append([
            Paragraph(str(i), S['muted']),
            Paragraph(name_text, S['body']),
            Paragraph(item.get('cluster',''), S['muted']),
            Paragraph(ps, S['muted'] if is_opt else S['body']),
        ])

    # Summenzeilen
    rows.append([Paragraph(''), Paragraph(''), Paragraph('<b>Einmalig gesamt</b>', S['muted']),
                 Paragraph(f'<b>{money(one_time)}</b>', S['price'])])
    if monthly > 0:
        rows.append([Paragraph(''), Paragraph(''), Paragraph('<b>Monatlich gesamt</b>', S['muted']),
                     Paragraph(f'<b>{money(monthly)}</b>', S['price'])])

    t = Table(rows, colWidths=[10*mm, 95*mm, 40*mm, 30*mm])
    # Summenzeilen: 1 wenn kein monthly, 2 wenn monthly vorhanden
    n_sum_rows = 2 if monthly > 0 else 1
    n_rows     = len(rows)
    sum_start  = n_rows - n_sum_rows  # Index der ersten Summenzeile

    ts = TableStyle([
        ('BACKGROUND',(0,0),(-1,0),BG),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('FONTSIZE',(0,0),(-1,0),7.5),
        ('LINEBELOW',(0,0),(-1,0),0.5,LINE),
        ('LINEBELOW',(0,1),(- 1,sum_start-1),0.3,LINE),   # Optionszeilen
        ('LINEABOVE',(0,sum_start),(-1,-1),0.8,RED),       # Linie vor Summen
        ('BACKGROUND',(0,sum_start),(-1,-1),colors.HexColor('#fff1f2')),  # Summen rosa
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
        ('ALIGN',(3,0),(3,-1),'RIGHT'),
    ])
    t.setStyle(ts)
    story.append(t)
    story.append(PageBreak())

    # ── Detailseiten ──────────────────────────────────────────────────────────
    section_title(story, '2. Detailbeschreibungen', S, CW)

    for i, item in enumerate(offer, 1):
        display = (item.get('display_type') or 'Großes Bild + Beschreibung').strip()
        name    = item.get('name','')
        short   = item.get('short_text','') or ''
        long_t  = item.get('long_text','')  or ''
        p       = item.get('price') or 0
        orig_p  = item.get('original_price') or p
        if item.get('optional'):
            ps = f'optional ({money(orig_p)}{"./Mo" if item.get("recurring") else ""})'
        else:
            ps = 'inklusive' if orig_p==0 else (money(orig_p)+'/Mo.' if item.get('recurring') else money(orig_p))

        # Jede Option wird als Block gesammelt und mit KeepTogether eingefügt.
        # So startet eine Option immer auf einer neuen Seite wenn sie nicht mehr passt –
        # unabhängig von den konfigurierbaren Seitenrändern.
        block = []

        block.append(Paragraph(f"{i}. {name}", S['h2']))
        block.append(Spacer(1, 2*mm))

        img_raw = fetch_image(item.get('image_path',''))

        # ── Variante 1: Großes Bild oben, dann Kurz- und Langtext ────────────
        if display in ('Großes Bild + Beschreibung', ''):
            img = make_image(img_raw, max_w=CW, max_h=100*mm)
            if img:
                block.append(img)
                block.append(Spacer(1, 3*mm))
            if short:
                block.append(Paragraph(f"<b>{short}</b>", S['body']))
                block.append(Spacer(1, 1*mm))
            if long_t:
                block.append(Paragraph(long_t, S['body']))

        # ── Variante 2: Kleines Bild links, Langtext rechts daneben ──────────
        elif display == 'Kleines Bild + Langtext':
            img = make_image(img_raw, max_w=70*mm, max_h=55*mm)
            text_parts = []
            if short:
                text_parts.append(Paragraph(f"<b>{short}</b>", S['body']))
                text_parts.append(Spacer(1, 2*mm))
            if long_t:
                text_parts.append(Paragraph(long_t, S['body']))

            if img and text_parts:
                img_col_w = min(img.drawWidth + 5*mm, 80*mm)
                t2 = Table([[img, text_parts]], colWidths=[img_col_w, CW - img_col_w])
                t2.setStyle(TableStyle([
                    ('VALIGN',       (0,0),(-1,-1),'TOP'),
                    ('LEFTPADDING',  (1,0),(1,0),   10),
                    ('TOPPADDING',   (0,0),(-1,-1),  0),
                    ('BOTTOMPADDING',(0,0),(-1,-1),  0),
                ]))
                block.append(t2)
            elif img:
                block.append(img)
                block.append(Spacer(1, 2*mm))
                for tp in text_parts: block.append(tp)
            else:
                for tp in text_parts: block.append(tp)

        # ── Variante 3: Kein Bild – Langtext + Kurztext ───────────────────────
        elif display == 'Kein Bild, Langtext + Kurztext':
            if long_t:
                block.append(Paragraph(long_t, S['body']))
                block.append(Spacer(1, 2*mm))
            if short:
                block.append(Paragraph(f"<i>{short}</i>", S['muted']))

        # ── Variante 4: Kein Bild – nur Kurztext ─────────────────────────────
        elif display == 'Kein Bild, Kurztext':
            if short:
                block.append(Paragraph(short, S['body']))

        # Fallback
        else:
            if short:  block.append(Paragraph(f"<b>{short}</b>", S['body']))
            if long_t: block.append(Paragraph(long_t, S['body']))

        # Dokumente dieser Option
        docs = item.get('documents') or []
        if docs:
            block.append(Spacer(1, 1*mm))
            doc_names = ', '.join(d.get('title','') for d in docs if d.get('title'))
            block.append(Paragraph(f"📎 Dokumente: {doc_names}", S['muted']))

        # Trennzeile + Preis
        block.append(Spacer(1, 2*mm))
        block.append(Paragraph(
            f"Preis: <b>{ps}</b>  ·  Cluster: {item.get('cluster','')}",
            S['muted']))
        block.append(Table([['']], colWidths=[CW],
            style=[('LINEBELOW',(0,0),(-1,-1),0.3,LINE),
                   ('TOPPADDING',(0,0),(-1,-1),2),
                   ('BOTTOMPADDING',(0,0),(-1,-1),0)]))
        block.append(Spacer(1, 5*mm))

        # KeepTogether: Block passt auf Seite → bleibt zusammen.
        # Passt er nicht → neue Seite, dann der Block.
        # Bei sehr langen Blöcken (z.B. Variante 1 mit großem Bild + viel Text)
        # wird automatisch aufgeteilt wenn nötig.
        try:
            story.append(KeepTogether(block))
        except Exception:
            # Fallback falls KeepTogether den Block nicht verarbeiten kann
            story.extend(block)
    story.append(PageBreak())

    # ── Preiszusammenfassung ──────────────────────────────────────────────────
    section_title(story, '3. Preiszusammenfassung', S, CW)
    servicevertrag = 0  # wird über Optionsbibliothek abgewickelt
    preis_rows = [
        [Paragraph('<b>Einmalige Kosten</b>', S['h3']), Paragraph(f'<b>{money(one_time)}</b>', S['price'])],
        [Paragraph('<b>Monatliche Kosten</b>', S['h3']), Paragraph(f'<b>{money(monthly)}</b>',  S['price'])],
    ]
    t = Table(preis_rows, colWidths=[CW-40*mm, 40*mm])
    t.setStyle(TableStyle([
        ('LINEBELOW',(0,0),(-1,-1),0.5,LINE),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#fff1f2')),
        ('BACKGROUND',(0,1),(-1,1),colors.HexColor('#fff1f2')),
    ]))
    story.append(t)
    story.append(Spacer(1,2*mm))
    story.append(Paragraph('Alle Preise verstehen sich exkl. gesetzlicher MwSt.', S['muted']))
    story.append(PageBreak())

    # ── Anlagen ───────────────────────────────────────────────────────────────
    section_title(story, '4. Anlagen', S, CW)

    # ZIP + Download-Link generieren
    download_url = None
    pkg_result   = {}
    if all_attachments:
        try:
            pkg_result   = _dl.create_download_package(
                offer_no        = project.get('offerNo', 'ENTWURF'),
                all_attachments = all_attachments,
                pdf_bytes       = None,
                pdf_filename    = filename,
            )
            download_url = pkg_result.get('zip_url', '') or None
        except Exception as e:
            print(f"ZIP generation failed: {e}")

    if all_attachments:
        # Anlage-Liste
        for a in all_attachments:
            label = a.get('title','')
            if a.get('_mandatory'):
                label += '  [Pflichtanlage]'
            story.append(Paragraph(f"• <b>{label}</b>", S['body']))
            if a.get('description'):
                story.append(Paragraph(a['description'], S['muted']))
            if a.get('_from_option'):
                story.append(Paragraph(f"Zugehörig zu: {a['_from_option']}", S['muted']))
            story.append(Spacer(1, 1*mm))

        # Download-Link + QR-Code
        if download_url:
            story.append(Spacer(1, 6*mm))

            # Trennlinie
            story.append(Table([['']], colWidths=[CW],
                style=[('LINEBELOW',(0,0),(-1,-1),0.5,RED),
                       ('TOPPADDING',(0,0),(-1,-1),0),
                       ('BOTTOMPADDING',(0,0),(-1,-1),2)]))
            story.append(Spacer(1, 4*mm))

            # QR-Code generieren
            qr_buf = _dl.generate_qr_code(download_url)

            # Layout: QR links, Text rechts
            qr_col_w = 40*mm
            text_col = [
                Paragraph('<b>Alle Dokumente herunterladen</b>', S['h3']),
                Spacer(1, 2*mm),
                Paragraph(
                    f'Scannen Sie den QR-Code oder verwenden Sie folgenden Link, '
                    f'um alle Anlagen als ZIP-Paket herunterzuladen.',
                    S['body']),
                Spacer(1, 3*mm),
                Paragraph(
                    f'<font size="7" color="#71717a">{download_url[:80]}{"..." if len(download_url)>80 else ""}</font>',
                    S['body']),
                Spacer(1, 2*mm),
                Paragraph(
                    '<font size="7" color="#71717a">Link gültig für 30 Tage</font>',
                    S['muted']),
            ]

            if qr_buf:
                qr_img = RLImage(qr_buf, width=35*mm, height=35*mm)
                t_qr   = Table([[qr_img, text_col]], colWidths=[qr_col_w, CW - qr_col_w])
                t_qr.setStyle(TableStyle([
                    ('VALIGN',      (0,0),(-1,-1),'MIDDLE'),
                    ('LEFTPADDING', (1,0),(1,0),   10),
                    ('TOPPADDING',  (0,0),(-1,-1),  0),
                    ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                ]))
                story.append(t_qr)
            else:
                for el in text_col: story.append(el)
    else:
        story.append(Paragraph('Keine Anlagen ausgewählt.', S['muted']))
    # ── AGB ───────────────────────────────────────────────────────────────────
    section_title(story, '5. Rechtliche Hinweise', S, CW)
    agb = legal or (
        'Die ausgewiesenen Preise sind Nettopreise und verstehen sich zuzüglich der gesetzlichen '
        'Mehrwertsteuer. Die Distribution entscheidet Sielaff Austria GmbH. Es gelten die '
        'allgemeinen Geschäftsbedingungen der Sielaff Austria GmbH in der jeweils gültigen Fassung.'
    )
    for para in agb.split('\n'):
        if para.strip():
            story.append(Paragraph(para.strip(), S['body']))

    # ── Build ─────────────────────────────────────────────────────────────────
    doc.build(story, canvasmaker=MyCanvas)
    content_buf.seek(0)

    try:
        from pypdf import PdfReader, PdfWriter
        writer = PdfWriter()
        for buf in [cover_buf, content_buf]:
            for page in PdfReader(buf).pages:
                writer.add_page(page)
        with open(filepath, 'wb') as f:
            writer.write(f)
    except Exception:
        with open(filepath, 'wb') as f:
            f.write(content_buf.read())

    # PDF auch in Supabase Storage hochladen für dauerhaften Zugriff
    supabase_pdf_url = ''
    try:
        supabase_url = os.environ.get('SUPABASE_URL', '')
        service_key  = os.environ.get('SUPABASE_SERVICE_KEY', '')
        if supabase_url and service_key:
            with open(filepath, 'rb') as f:
                pdf_bytes_upload = f.read()
            upload_res = httpx.post(
                f"{supabase_url}/storage/v1/object/pdfs/{filename}",
                content=pdf_bytes_upload,
                headers={
                    'Authorization': f'Bearer {service_key}',
                    'Content-Type': 'application/pdf',
                },
                timeout=60,
            )
            if upload_res.status_code in (200, 201):
                # Signierte URL (1 Jahr)
                sign_res = httpx.post(
                    f"{supabase_url}/storage/v1/object/sign/pdfs/{filename}",
                    headers={'Authorization': f'Bearer {service_key}', 'Content-Type': 'application/json'},
                    json={'expiresIn': 365 * 24 * 3600},
                    timeout=15,
                )
                if sign_res.status_code == 200:
                    signed = sign_res.json().get('signedURL', '')
                    if signed.startswith('/'):
                        signed = f"{supabase_url}/storage/v1{signed}"
                    supabase_pdf_url = signed
    except Exception as e:
        print(f"PDF Supabase Upload failed: {e}")

    # PDF Bytes für ZIP direkt mitlesen (bevor Datei evtl. weg ist)
    try:
        with open(filepath, 'rb') as _f:
            _pdf_bytes_final = _f.read()
    except Exception:
        _pdf_bytes_final = b''

    return {
        'ok':             True,
        'download_url':   supabase_pdf_url or f'/api/pdf/download/{filename}',
        'local_filename': filename,
        'pdf_bytes':      _pdf_bytes_final,  # direkt im Speicher, kein Disk-Zugriff nötig
        'package_url':    download_url or '',
        'zip_filename':   pkg_result.get('zip_filename',''),
        'expires_at':     pkg_result.get('expires_at',''),
    }


def get_pdf_path(filename: str) -> str | None:
    path = os.path.join(EXPORT_DIR, filename)
    return path if os.path.exists(path) else None
