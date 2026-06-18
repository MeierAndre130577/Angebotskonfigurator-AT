"""
PDF-Generierung – Angebotskonfigurator Sielaff Austria v5
- Deckblatt: komplett weißes Design
- Kopfzeile: topMargin korrekt
- Summe in Angebotsübersicht
- Anlagen aus Optionsdokumenten (dedupliziert)
"""

import os, uuid, io, gc, httpx
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
    Zeichnet ein Linien-Icon zentriert bei (cx, cy) in Rot.
    kind: 'doc' | 'cal' | 'company' | 'brief' | 'badge' | 'clock' | 'tag'
    """
    C_RED = colors.HexColor('#E30613')
    c.setStrokeColor(C_RED)
    c.setFillColor(C_RED)
    c.setLineWidth(0.9)

    if kind == 'doc':
        # Dokument mit Eselsohr oben rechts + drei Zeilen
        c.setFillColor(colors.HexColor('#FAEAEA'))
        pts = [(cx-5, cy-7), (cx+2, cy-7), (cx+5, cy-4),
               (cx+5, cy+7), (cx-5, cy+7)]
        path = c.beginPath()
        path.moveTo(*pts[0])
        for pt in pts[1:]: path.lineTo(*pt)
        path.close()
        c.drawPath(path, fill=1, stroke=0)
        c.setStrokeColor(C_RED)
        path2 = c.beginPath()
        path2.moveTo(*pts[0])
        for pt in pts[1:]: path2.lineTo(*pt)
        path2.close()
        c.drawPath(path2, fill=0, stroke=1)
        # Eselsohr
        c.line(cx+2, cy-7, cx+2, cy-4)
        c.line(cx+2, cy-4, cx+5, cy-4)
        # Textzeilen
        for dy in (cy+3, cy, cy-2):
            c.line(cx-3, dy, cx+3, dy)

    elif kind == 'cal':
        # Kalender: Rechteck + Trennlinie + Bügelchen + Punkte
        c.rect(cx-6, cy-6, 12, 12, fill=0, stroke=1)
        c.line(cx-6, cy-1, cx+6, cy-1)
        c.line(cx-3, cy+7, cx-3, cy+5)
        c.line(cx+3, cy+7, cx+3, cy+5)
        # Kalenderblatt-Punkte
        for dx in (-2, 2):
            for dy in (cy-3, cy-6):
                c.circle(cx+dx, dy+1, 1, fill=1, stroke=0)

    elif kind == 'company':
        # Gebäude: Hauptkörper + Dach + Tür + Fenster
        c.rect(cx-6, cy-7, 12, 11, fill=0, stroke=1)
        # Dach-Dreieck
        path = c.beginPath()
        path.moveTo(cx-7, cy+4)
        path.lineTo(cx,   cy+9)
        path.lineTo(cx+7, cy+4)
        c.drawPath(path, fill=0, stroke=1)
        # Tür
        c.rect(cx-2, cy-7, 4, 5, fill=0, stroke=1)
        # Fenster
        c.rect(cx-5, cy-1, 3, 3, fill=0, stroke=1)
        c.rect(cx+2, cy-1, 3, 3, fill=0, stroke=1)

    elif kind == 'brief':
        # Aktenkoffer: Koffer-Körper + Griff + mittlere Linie + Schloss
        c.roundRect(cx-6, cy-6, 12, 11, 1, fill=0, stroke=1)
        # Griff (Bogen oben)
        path = c.beginPath()
        path.moveTo(cx-3, cy+5)
        path.curveTo(cx-3, cy+9, cx+3, cy+9, cx+3, cy+5)
        c.drawPath(path, fill=0, stroke=1)
        c.line(cx-6, cy, cx+6, cy)
        c.circle(cx, cy+2, 1.5, fill=1, stroke=0)

    elif kind == 'badge':
        # Ausweis: Karte + Kopf-Silhouette
        c.roundRect(cx-6, cy-7, 12, 13, 1.5, fill=0, stroke=1)
        # Kopf
        c.circle(cx, cy+2, 2.5, fill=0, stroke=1)
        # Schultern
        path = c.beginPath()
        path.moveTo(cx-5, cy-5)
        path.curveTo(cx-5, cy-1, cx+5, cy-1, cx+5, cy-5)
        c.drawPath(path, fill=0, stroke=1)

    elif kind == 'clock':
        # Uhr: Kreis + zwei Zeiger + Mittelpunkt
        c.circle(cx, cy, 7, fill=0, stroke=1)
        c.line(cx, cy, cx, cy+5)        # Stundenzeiger
        c.line(cx, cy, cx+4, cy+2)     # Minutenzeiger
        c.circle(cx, cy, 1, fill=1, stroke=0)

    elif kind == 'tag':
        # Preisschild: Fünfeck + Loch
        path = c.beginPath()
        path.moveTo(cx-6, cy-5)
        path.lineTo(cx+2, cy-5)
        path.lineTo(cx+7, cy)
        path.lineTo(cx+2, cy+5)
        path.lineTo(cx-6, cy+5)
        path.close()
        c.drawPath(path, fill=0, stroke=1)
        c.circle(cx-3, cy, 1.5, fill=1, stroke=0)


# ── Leasing-Seite ────────────────────────────────────────────────────────────

def draw_leasing_section(story: list, leasing: dict, s: dict, S: dict, CW: float):
    """Leasing-Finanzierungsseite mit Ratenberechnung."""
    kaufpreis = float(leasing.get('kaufpreis', 0) or 0)
    durations = leasing.get('durations') or [36, 48, 60]
    _default_factors = {
        '36': {'10000': 3.2, '20000': 3.2, '30000': 3.2, '50000': 3.2, '999999': 3.2},
        '48': {'10000': 2.41,'20000': 2.41,'30000': 2.41,'50000': 2.41,'999999': 2.41},
        '60': {'10000': 2.0, '20000': 2.0, '30000': 2.0, '50000': 2.0, '999999': 2.0},
    }
    factors   = s.get('leasing_factors') or _default_factors
    proc_fee  = float(s.get('leasing_processing_fee', 100) or 100)
    vat_pct   = float(s.get('leasing_vat', 20) or 20)
    min_amt   = float(s.get('leasing_min_amount', 2000) or 2000)
    vat       = vat_pct / 100

    # Preisklasse ermitteln
    brackets = [10000, 20000, 30000, 50000, 999999]
    bracket  = next((b for b in brackets if kaufpreis <= b), 999999)
    b_key    = str(bracket)

    def calc(dur):
        dur_k   = str(dur)
        factor  = float((factors.get(dur_k) or {}).get(b_key, 0) or 0)
        monthly = round(kaufpreis * factor / 100, 2)
        legal   = round((36 * monthly * (1 + vat) + proc_fee * (1 + vat)) * 0.01, 2)
        return monthly, proc_fee, legal

    GRAY_BG = colors.HexColor('#F4F4F5')
    PINK_BG = colors.HexColor('#fff1f2')

    # Intro-Text (optional, aus Einstellungen)
    intro_text = (s.get('leasing_intro_text') or '').strip()
    if intro_text:
        story.append(Paragraph(intro_text, S['body']))
        story.append(Spacer(1, 4 * mm))

    # Kaufpreis
    story.append(Paragraph(
        f'Kaufpreis exkl. USt: <b>{money(kaufpreis)}</b>'
        f'&nbsp;&nbsp;&nbsp;<font size="8" color="#71717a">Mindestbetrag {money(min_amt)} exkl. USt</font>',
        S['body']
    ))
    story.append(Spacer(1, 4 * mm))

    # Berechnungstabelle
    dur_list = [str(d) for d in durations]
    n_dur    = len(dur_list)
    label_w  = 75 * mm
    col_w    = (CW - label_w) / n_dur

    hdr = [Paragraph('', S['muted'])] + [
        Paragraph(f'<b>{d} Monate</b>', S['h3']) for d in dur_list
    ]
    results = {d: calc(int(d)) for d in dur_list}

    rows = [
        hdr,
        [Paragraph('<b>Leasingrate p.M. exkl. USt</b>', S['body'])] +
        [Paragraph(f'<b>{money(results[d][0])}</b>', S['body']) for d in dur_list],
        [Paragraph('Einmalige Bearbeitungsgebühr exkl. USt', S['body'])] +
        [Paragraph(money(proc_fee), S['muted']) for d in dur_list],
        [Paragraph('Gesetzl. Rechtsgeschäftsgebühr', S['body'])] +
        [Paragraph(money(results[d][2]), S['muted']) for d in dur_list],
    ]

    t = Table(rows, colWidths=[label_w] + [col_w] * n_dur)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), GRAY_BG),
        ('BACKGROUND',    (0, 1), (-1, 1), PINK_BG),
        ('LINEBELOW',     (0, 0), (-1, -1), 0.5, LINE),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ('ALIGN',  (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t)
    story.append(Spacer(1, 5 * mm))

    # Hinweistexte
    hints = [
        'Leasingentgelt: Anschaffungskosten x Leasingfaktor / 100',
        f'Einmaliges Bearbeitungsentgelt: {money(proc_fee)} exkl. {int(vat_pct)} % USt bei Vertragsbeginn',
        'Gesetzliche Mietvertragsgebühr: 1 % von max. 36 Leasingentgelten inkl. USt + Nebengebühren',
        'Kalkulation basiert auf dem 3-Monats-Euribor. Anpassung des Leasingentgeltes vierteljährlich.',
    ]
    for h in hints:
        story.append(Paragraph(f'• {h}', S['muted']))
        story.append(Spacer(1, 1 * mm))

    # Ansprechpartner
    contacts = []
    for n in ['1', '2']:
        name = (s.get(f'leasing_contact{n}_name') or '').strip()
        if name:
            contacts.append({
                'name':    name,
                'address': (s.get(f'leasing_contact{n}_address') or '').strip(),
                'phone':   (s.get(f'leasing_contact{n}_phone') or '').strip(),
                'email':   (s.get(f'leasing_contact{n}_email') or '').strip(),
            })

    if contacts:
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(
            'Ihre Ansprechpartner für Fragen und Abwicklung:',
            S['body']
        ))
        story.append(Spacer(1, 3 * mm))
        cells = []
        for c in contacts:
            lines = [Paragraph(f'<b>{c["name"]}</b>', S['body'])]
            if c['address']: lines.append(Paragraph(c['address'], S['muted']))
            if c['phone']:   lines.append(Paragraph(f'Tel: {c["phone"]}', S['muted']))
            if c['email']:   lines.append(Paragraph(c['email'], S['muted']))
            cells.append(lines)
        while len(cells) < 2:
            cells.append([Paragraph('', S['muted'])])
        half = CW / 2
        tc = Table([cells], colWidths=[half, half])
        tc.setStyle(TableStyle([
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ('BOX',           (0, 0), (0, 0),   0.5, LINE),
            ('BOX',           (1, 0), (1, 0),   0.5, LINE),
            ('TOPPADDING',    (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING',   (0, 0), (-1, -1), 10),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
        ]))
        story.append(tc)


# ── Deckblatt – Diagonaler Schnitt ───────────────────────────────────────────

def draw_cover(c: canvas.Canvas, data: dict):
    """
    Deckblatt – Diagonaler Schnitt:
    - Weißer linker Bereich / Foto rechts / rote Akzentlinie
    - Logo + ANGEBOT oben links
    - Info-Box vertikal zentriert, kein Rahmen, mit Icons
    - Fußzeile: 2 Spalten mit Icons (Gebäude | Briefumschlag)
    """
    from PIL import Image as PILImage

    project  = data.get('project')  or {}
    provider = data.get('provider') or {}

    C_RED    = colors.HexColor('#E30613')
    C_DARK   = colors.HexColor('#1D1D1B')
    C_MUTED  = colors.HexColor('#5A5A5A')
    C_FOOTER = colors.HexColor('#E8E8E8')
    C_ICON   = colors.HexColor('#FAEAEA')
    C_SHADOW = colors.HexColor('#C8C8C8')

    FOOTER_H   = 72
    MARGIN     = 38
    LOGO_SIZE  = 52

    # Diagonale: oben bei x=DIAG_TOP (y=H), unten bei x=DIAG_BOT (y=FOOTER_H)
    DIAG_TOP = 375.0
    DIAG_BOT = 490.0

    # Foto-Bereich: ab DIAG_TOP mit etwas Überlapp nach links
    IMG_X = DIAG_TOP - 10
    IMG_Y = FOOTER_H
    IMG_W = W - IMG_X
    IMG_H = H - FOOTER_H

    # ── 1. Weißer Hintergrund ─────────────────────────────────────────────────
    c.setFillColor(colors.white)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # ── 2. Cover-Foto (rechte Seite) ─────────────────────────────────────────
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
        except Exception as e:
            print(f'[draw_cover] Bild-Fehler: {e}')
            c.setFillColor(colors.HexColor('#AABBCC'))
            c.rect(IMG_X, IMG_Y, IMG_W, IMG_H, fill=1, stroke=0)
    else:
        c.setFillColor(colors.HexColor('#AABBCC'))
        c.rect(IMG_X, IMG_Y, IMG_W, IMG_H, fill=1, stroke=0)
    c.restoreState()

    # ── 3. Weiße Trapez-Maske (linker Bereich) ───────────────────────────────
    c.saveState()
    c.setFillColor(colors.white)
    mask = c.beginPath()
    mask.moveTo(0, H)
    mask.lineTo(DIAG_TOP, H)
    mask.lineTo(DIAG_BOT, FOOTER_H)
    mask.lineTo(0, FOOTER_H)
    mask.close()
    c.drawPath(mask, fill=1, stroke=0)
    c.restoreState()

    # ── 4. Diagonale Akzentlinie (Schatten + Rot) ────────────────────────────
    c.setStrokeColor(C_SHADOW)
    c.setLineWidth(3)
    c.line(DIAG_TOP + 4, H, DIAG_BOT + 4, FOOTER_H)
    c.setStrokeColor(C_RED)
    c.setLineWidth(3)
    c.line(DIAG_TOP, H, DIAG_BOT, FOOTER_H)

    # ── 5. Logo oben links ────────────────────────────────────────────────────
    LOGO_X = MARGIN
    LOGO_Y = H - 35 - LOGO_SIZE   # Unterkante des Logos

    c.saveState()
    logo_url = provider.get('logo_image') or ''
    logo_img = fetch_image(logo_url) if logo_url else None
    if logo_img:
        try:
            logo_img.seek(0)
            lb = logo_img.read()
            pil_l = PILImage.open(io.BytesIO(lb))
            lw, lh = pil_l.size
            sc = min(1.0, LOGO_SIZE / (lw / 96 * 72), LOGO_SIZE / (lh / 96 * 72))
            fw = lw / 96 * 72 * sc
            fh = lh / 96 * 72 * sc
            c.drawImage(ImageReader(io.BytesIO(lb)),
                        LOGO_X, LOGO_Y + (LOGO_SIZE - fh) / 2,
                        width=fw, height=fh,
                        preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f'[draw_cover] Logo-Fehler: {e}')
            c.setFillColor(C_RED)
            c.rect(LOGO_X, LOGO_Y, LOGO_SIZE, LOGO_SIZE, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont('Helvetica-Bold', 10)
            c.drawCentredString(LOGO_X + LOGO_SIZE/2, LOGO_Y + LOGO_SIZE/2 - 3, 'LOGO')
    else:
        c.setFillColor(C_RED)
        c.rect(LOGO_X, LOGO_Y, LOGO_SIZE, LOGO_SIZE, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont('Helvetica-Bold', 10)
        c.drawCentredString(LOGO_X + LOGO_SIZE/2, LOGO_Y + LOGO_SIZE/2 - 3, 'LOGO')
    c.restoreState()

    # ── 7. Info-Box – Position zuerst berechnen (Basis für Titel-Zentrierung) ──
    BOX_X  = MARGIN
    BOX_W  = 310
    ROW_H  = 48
    info_rows = [
        ('doc',     'Angebotsnummer', project.get('offerNo',   '')),
        ('cal',     'Datum',          project.get('date',       '')),
        ('company', 'Kunde',          project.get('customer',   '')),
        ('brief',   'Projekt',        project.get('project',    '')),
        ('badge',   'Ansprechpartner',project.get('contact',    '')),
        ('clock',   'Gültig bis',     project.get('valid',      '')),
        ('tag',     'Version',        project.get('version',    '1.0')),
    ]
    BOX_H = ROW_H * len(info_rows) + 20
    TITLE_BLOCK_H = 90                 # geschätzte Höhe: ANGEBOT + Linie + Untertitel
    AVAILABLE = LOGO_Y - FOOTER_H      # freier Raum zwischen Logo-Unterkante und Fußzeile
    GAP = max(20, (AVAILABLE - TITLE_BLOCK_H - BOX_H) / 3)  # 3 gleiche Abstände
    BOX_Y = FOOTER_H + GAP            # Info-Block zentriert zwischen Titel und Fußzeile
    BOX_TOP = BOX_Y + BOX_H

    # ── 6. ANGEBOT + Dekorlinie + Untertitel – mittig zwischen Logo und Box ──
    # Titelblock-Höhe: Oberkante ANGEBOT (+42pt) bis Unterkante Untertitel (-41pt) ≈ 83pt
    TITLE_BLOCK_H = 83
    LOGO_BOT = LOGO_Y                  # Unterkante Logo
    # Mitte des freien Raums zwischen Logo-Unterkante und Box-Oberkante:
    TITLE_MID  = (LOGO_BOT + BOX_TOP) / 2
    TITLE_BASE = TITLE_MID - 1        # ANGEBOT-Baseline liegt nahe der Blockmitte

    c.setFillColor(C_DARK)
    c.setFont('Times-Roman', 58)
    c.drawString(MARGIN, TITLE_BASE, 'ANGEBOT')

    LINE_Y = TITLE_BASE - 14
    c.setStrokeColor(C_RED)
    c.setLineWidth(2)
    c.line(MARGIN, LINE_Y, MARGIN + 75, LINE_Y)

    SUB_Y = LINE_Y - 18
    c.setFont('Helvetica', 11)
    c.setFillColor(C_MUTED)
    c.drawString(MARGIN, SUB_Y, 'Maßgeschneiderte Lösung für Ihr Vorhaben')

    ICON_CX = BOX_X + 18
    for i, (icon_kind, label, value) in enumerate(info_rows):
        # Zeile von oben: erste Zeile liegt oben
        row_cy = BOX_Y + BOX_H - 20 - i * ROW_H - ROW_H / 2

        # Icon-Kreis (hellrot + roter Rand)
        c.setFillColor(C_ICON)
        c.circle(ICON_CX, row_cy, 12, fill=1, stroke=0)
        c.setStrokeColor(colors.HexColor('#E30613'))
        c.setLineWidth(0.8)
        c.circle(ICON_CX, row_cy, 12, fill=0, stroke=1)
        _draw_icon(c, ICON_CX, row_cy, icon_kind)

        c.setFont('Helvetica-Bold', 10)
        c.setFillColor(C_DARK)
        c.drawString(BOX_X + 36, row_cy - 4, label)

        c.setFont('Helvetica', 10)
        c.setFillColor(C_DARK)
        c.drawString(BOX_X + 162, row_cy - 4, str(value)[:40])

    # ── 8. Fußzeile ───────────────────────────────────────────────────────────
    c.setFillColor(C_FOOTER)
    c.rect(0, 0, W, FOOTER_H, fill=1, stroke=0)

    # Rote Oberlinie
    c.setStrokeColor(C_RED)
    c.setLineWidth(2)
    c.line(0, FOOTER_H, W, FOOTER_H)

    # Mittlere Trennlinie
    MID_X = W / 2
    c.setStrokeColor(C_SHADOW)
    c.setLineWidth(0.5)
    c.line(MID_X, 10, MID_X, FOOTER_H - 10)

    FTR_ICY = FOOTER_H / 2   # Icon vertikal zentriert

    def _footer_icon(kind, icx, icy):
        c.setStrokeColor(C_MUTED)
        c.setFillColor(C_MUTED)
        c.setLineWidth(0.8)
        if kind == 'building':
            c.rect(icx-9, icy-8, 18, 14, fill=0, stroke=1)
            c.rect(icx-2, icy-8, 4,  7, fill=0, stroke=1)
            c.rect(icx-7, icy-1, 4,  4, fill=0, stroke=1)
            c.rect(icx+3, icy-1, 4,  4, fill=0, stroke=1)
            roof = c.beginPath()
            roof.moveTo(icx-10, icy+6)
            roof.lineTo(icx,    icy+13)
            roof.lineTo(icx+10, icy+6)
            c.drawPath(roof, fill=0, stroke=1)
        elif kind == 'envelope':
            c.rect(icx-10, icy-7, 20, 14, fill=0, stroke=1)
            flap = c.beginPath()
            flap.moveTo(icx-10, icy+7)
            flap.lineTo(icx,    icy-1)
            flap.lineTo(icx+10, icy+7)
            c.drawPath(flap, fill=0, stroke=1)

    # Linke Spalte: Gebäude-Icon + Firma
    CL_ICON = MARGIN + 9
    CL_TEXT = MARGIN + 32
    _footer_icon('building', CL_ICON, FTR_ICY)

    c.setFont('Helvetica-Bold', 8)
    c.setFillColor(C_DARK)
    c.drawString(CL_TEXT, FOOTER_H - 18, provider.get('company', ''))
    c.setFont('Helvetica', 7)
    c.setFillColor(C_MUTED)
    addr = provider.get('address', '')
    if ',' in addr:
        parts = addr.split(',', 1)
        c.drawString(CL_TEXT, FOOTER_H - 28, parts[0].strip() + ',')
        c.drawString(CL_TEXT, FOOTER_H - 38, parts[1].strip())
    else:
        c.drawString(CL_TEXT, FOOTER_H - 28, addr)
    uid = provider.get('uid', '') or provider.get('UID', '')
    if uid:
        c.drawString(CL_TEXT, FOOTER_H - 50, f'UID: {uid}')

    # Rechte Spalte: Briefumschlag-Icon + Kontakt
    CR_ICON = MID_X + 20 + 9
    CR_TEXT = MID_X + 20 + 32
    _footer_icon('envelope', CR_ICON, FTR_ICY)

    c.setFont('Helvetica-Bold', 8)
    c.setFillColor(C_DARK)
    c.drawString(CR_TEXT, FOOTER_H - 18, 'Kontakt')
    c.setFont('Helvetica', 7)
    c.setFillColor(C_MUTED)
    c.drawString(CR_TEXT, FOOTER_H - 28, f'Tel:   {provider.get("phone",   "")}')
    c.drawString(CR_TEXT, FOOTER_H - 38, f'Mail:  {provider.get("email",   "")}')
    c.drawString(CR_TEXT, FOOTER_H - 50, f'Web:   {provider.get("website", "")}')

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
    leasing     = data.get('leasing')      or {}
    leasing_on  = bool(leasing.get('enabled', False))

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

    # Inhaltsverzeichnis – dynamisch je nach Leasing
    # Reihenfolge: Übersicht → [Leasing] → Preiszusammenfassung → Detailbeschreibungen → Anlagen → AGB
    _sn = 2
    _toc = [('1', 'Angebotsübersicht')]
    if leasing_on:
        _toc.append((str(_sn), 'Leasing-Finanzierung')); _sn += 1
    _toc.append((str(_sn), 'Preiszusammenfassung')); _sn += 1
    _toc.append((str(_sn), 'Detailbeschreibungen')); _sn += 1
    _toc.append((str(_sn), 'Anlagen'));               _sn += 1
    _toc.append((str(_sn), 'Rechtliche Hinweise'))
    # Sektionsnummern merken
    _sec_leasing = 2 if leasing_on else None
    _sec_preis   = 3 if leasing_on else 2
    _sec_detail  = 4 if leasing_on else 3
    _sec_anlagen = 5 if leasing_on else 4
    _sec_agb     = 6 if leasing_on else 5

    section_title(story, 'Inhaltsverzeichnis', S, CW)
    for num, label in _toc:
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
    payment_term = project.get('payment_term', '')
    if payment_term:
        story.append(Spacer(1, 3*mm))
        story.append(Paragraph(f'Zahlungsziel: {payment_term}', S['muted']))
    story.append(PageBreak())

    # ── Leasing-Finanzierung (optional) ──────────────────────────────────────
    if leasing_on:
        section_title(story, f'{_sec_leasing}. Leasing-Finanzierung', S, CW)
        draw_leasing_section(story, leasing, s, S, CW)
        story.append(PageBreak())

    # ── Preiszusammenfassung ──────────────────────────────────────────────────
    section_title(story, f'{_sec_preis}. Preiszusammenfassung', S, CW)

    # Kundenlogo laden
    cust_logo_url = project.get('customer_logo', '')
    logo_img = None
    if cust_logo_url:
        ld = fetch_image(cust_logo_url)
        logo_img = make_image(ld, 32*mm, 22*mm) if ld else None

    # Kundendaten aufbauen
    cust_name    = project.get('customer', '')
    cust_contact = project.get('contact', '')
    cust_pos     = project.get('customer_position', '')
    cust_email   = project.get('customerEmail', '')
    cust_phone   = project.get('customer_phone', '')
    cust_mobile  = project.get('customer_mobile', '')
    cust_street  = project.get('customer_street', '')
    cust_zip     = project.get('customer_zip', '')
    cust_city    = project.get('customer_city', '')
    cust_web     = project.get('customer_website', '')

    cust_cells = []
    if cust_name:    cust_cells.append(Paragraph(f'<b>{cust_name}</b>', S['h2']))
    if cust_contact:
        contact_line = cust_contact + (f', {cust_pos}' if cust_pos else '')
        cust_cells.append(Paragraph(contact_line, S['body']))
    addr = ', '.join(filter(None, [cust_street, f'{cust_zip} {cust_city}'.strip()]))
    if addr:         cust_cells.append(Paragraph(addr, S['body']))
    if cust_email:   cust_cells.append(Paragraph(cust_email, S['muted']))
    tel = ' · '.join(filter(None, [
        f'Tel: {cust_phone}'   if cust_phone  else '',
        f'Mobil: {cust_mobile}' if cust_mobile else '',
    ]))
    if tel:          cust_cells.append(Paragraph(tel, S['muted']))
    if cust_web:     cust_cells.append(Paragraph(cust_web, S['muted']))
    if not cust_cells: cust_cells = [Paragraph('', S['body'])]

    logo_col_w = 36*mm if logo_img else 0
    info_col_w = CW - logo_col_w
    if logo_img:
        hdr_t = Table([[cust_cells, logo_img]], colWidths=[info_col_w, logo_col_w])
        hdr_t.setStyle(TableStyle([
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('ALIGN',(1,0),(1,0),'RIGHT'),
            ('TOPPADDING',(0,0),(-1,-1),0),
            ('BOTTOMPADDING',(0,0),(-1,-1),0),
        ]))
    else:
        hdr_t = Table([[[*cust_cells]]], colWidths=[CW])
        hdr_t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP')]))
    story.append(hdr_t)
    story.append(Spacer(1, 5*mm))

    # Preistabelle
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
    if payment_term:
        story.append(Spacer(1,2*mm))
        story.append(Paragraph(f'Zahlungsziel: {payment_term}', S['muted']))

    # Lieferadresse
    delivery_address = project.get('delivery_address', '')
    if delivery_address:
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph('<b>Lieferadresse</b>', S['h3']))
        story.append(Paragraph(delivery_address, S['body']))

    # Unterschrift / Rechtsverbindliche Bestellung
    order_style = ParagraphStyle('order', fontName='Helvetica-Bold', fontSize=11, textColor=DARK)
    sig_block = [
        Spacer(1, 14*mm),
        Table([[Paragraph('Rechtsverbindliche Bestellung', order_style)]],
              colWidths=[CW],
              style=[('BACKGROUND',(0,0),(-1,-1),BG),
                     ('LINEABOVE',(0,0),(-1,-1),1.5,RED),
                     ('TOPPADDING',(0,0),(-1,-1),7),
                     ('BOTTOMPADDING',(0,0),(-1,-1),7)]),
        Spacer(1, 3*mm),
        Paragraph(
            'Mit meiner Unterschrift bestätige ich die Richtigkeit der oben angeführten Angaben '
            'und beauftrage Sielaff Austria GmbH rechtsverbindlich mit der Lieferung der '
            'aufgeführten Produkte und Dienstleistungen zu den genannten Konditionen.',
            S['muted']),
        Spacer(1, 14*mm),
        Table([
            [Paragraph('Datum', S['muted']), Paragraph('Unterschrift &amp; Firmenstempel', S['muted'])],
            [Paragraph(project.get('date',''), S['body']), Paragraph('', S['body'])],
        ], colWidths=[CW*0.35, CW*0.65],
        style=[
            ('LINEBELOW',(0,1),(0,1),0.6,DARK),
            ('LINEBELOW',(1,1),(1,1),0.6,DARK),
            ('TOPPADDING',(0,0),(-1,-1),2),
            ('BOTTOMPADDING',(0,0),(-1,-1),8),
        ]),
    ]
    story.append(KeepTogether(sig_block))
    story.append(PageBreak())

    # ── Detailseiten ──────────────────────────────────────────────────────────
    section_title(story, f'{_sec_detail}. Detailbeschreibungen', S, CW)

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

    # ── Anlagen ───────────────────────────────────────────────────────────────
    section_title(story, f'{_sec_anlagen}. Anlagen', S, CW)

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
    section_title(story, f'{_sec_agb}. Rechtliche Hinweise', S, CW)
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

    # Speicher freigeben
    del story
    gc.collect()

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

