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
        return s
    except Exception:
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
    if not url: return None
    try:
        r = httpx.get(url, timeout=10, follow_redirects=True)
        if r.status_code == 200:
            return io.BytesIO(r.content)
    except Exception:
        pass
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

# ── Deckblatt – Komplett Weiß ─────────────────────────────────────────────────

def draw_cover(c: canvas.Canvas, data: dict):
    project  = data.get('project')  or {}
    provider = data.get('provider') or {}
    offer    = data.get('offer')    or []

    # Weißer Hintergrund
    c.setFillColor(WHITE)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Roter Streifen links (schmal, 5mm)
    c.setFillColor(RED)
    c.rect(0, 0, 5*mm, H, fill=1, stroke=0)

    # ── Logo + Firmenname oben ────────────────────────────────────────────────
    logo_x = 18*mm
    logo_y = H - 30*mm
    if os.path.exists(LOGO_PATH):
        try:
            c.drawImage(LOGO_PATH, logo_x, logo_y,
                       width=22*mm, height=22*mm,
                       preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    c.setFillColor(DARK)
    c.setFont('Helvetica-Bold', 11)
    c.drawString(logo_x + 26*mm, logo_y + 12*mm, provider.get('company', 'Sielaff Austria GmbH'))
    c.setFont('Helvetica', 8)
    c.setFillColor(MUTED)
    c.drawString(logo_x + 26*mm, logo_y + 5*mm, provider.get('address', ''))

    # Trennlinie unter Header
    c.setStrokeColor(LINE)
    c.setLineWidth(0.5)
    c.line(18*mm, H - 36*mm, W - 15*mm, H - 36*mm)

    # ── Foto rechts ───────────────────────────────────────────────────────────
    cover_url = project.get('coverImage', '')
    if not cover_url:
        for item in offer:
            if item.get('image_path'):
                cover_url = item['image_path']
                break

    img_x = W / 2
    img_y = H / 2 - 5*mm
    img_w = W / 2 - 15*mm
    img_h = H / 2 - 35*mm

    cover_img = fetch_image(cover_url)
    if cover_img:
        try:
            c.drawImage(cover_img, img_x, img_y, width=img_w, height=img_h,
                       preserveAspectRatio=False)
            c.setStrokeColor(LINE)
            c.setLineWidth(0.5)
            c.rect(img_x, img_y, img_w, img_h, fill=0, stroke=1)
        except Exception:
            c.setFillColor(BG)
            c.rect(img_x, img_y, img_w, img_h, fill=1, stroke=0)
    else:
        c.setFillColor(BG)
        c.rect(img_x, img_y, img_w, img_h, fill=1, stroke=0)
        c.setFillColor(MUTED)
        c.setFont('Helvetica', 9)
        c.drawCentredString(img_x + img_w/2, img_y + img_h/2, 'Produktfoto wird in der Konfiguration festgelegt')

    # ── Hauptinhalt links ─────────────────────────────────────────────────────
    cx = 18*mm
    cy = H / 2 + 28*mm

    # "ANGEBOT" Label
    c.setFillColor(RED)
    c.setFont('Helvetica-Bold', 7)
    c.drawString(cx, cy, 'ANGEBOT')
    c.rect(cx, cy - 2*mm, 16*mm, 0.8*mm, fill=1, stroke=0)

    # Kundenname
    c.setFillColor(DARK)
    font_size = 24 if len(project.get('customer','')) <= 22 else 18
    c.setFont('Helvetica-Bold', font_size)
    c.drawString(cx, cy - 13*mm, project.get('customer', ''))

    # Projektname
    c.setFillColor(MUTED)
    c.setFont('Helvetica', 12)
    c.drawString(cx, cy - 21*mm, project.get('project', ''))

    # Trennlinie
    c.setStrokeColor(LINE)
    c.setLineWidth(0.5)
    c.line(cx, cy - 27*mm, W/2 - 10*mm, cy - 27*mm)

    # Detail-Felder
    def detail(label, value, y):
        c.setFillColor(MUTED)
        c.setFont('Helvetica', 7)
        c.drawString(cx, y + 4*mm, label.upper())
        c.setFillColor(DARK)
        c.setFont('Helvetica-Bold', 9)
        c.drawString(cx, y, value or '—')

    detail('Angebotsnummer', project.get('offerNo',''),      cy - 37*mm)
    detail('Datum',          project.get('date',''),          cy - 49*mm)
    detail('Gültig bis',     project.get('valid',''),         cy - 61*mm)
    detail('Ansprechpartner',project.get('contact',''),       cy - 73*mm)
    detail('E-Mail',         project.get('customerEmail',''), cy - 85*mm)

    # ── Footer ────────────────────────────────────────────────────────────────
    c.setStrokeColor(LINE)
    c.setLineWidth(0.5)
    c.line(18*mm, 28*mm, W - 15*mm, 28*mm)
    c.setFillColor(MUTED)
    c.setFont('Helvetica', 7.5)
    footer = f"{provider.get('company','')}  ·  {provider.get('address','')}  ·  {provider.get('email','')}  ·  {provider.get('phone','')}"
    c.drawString(18*mm, 20*mm, footer)

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
    cover_buf = io.BytesIO()
    c_cover   = canvas.Canvas(cover_buf, pagesize=A4)
    draw_cover(c_cover, data)
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

    one_time = sum((i.get('price') or 0) for i in offer if not i.get('recurring'))
    monthly  = sum((i.get('price') or 0) for i in offer if i.get('recurring'))

    hdr  = [Paragraph(f'<b>{x}</b>', S['muted']) for x in ['#','Option','Cluster','Preis']]
    rows = [hdr]
    for i, item in enumerate(offer, 1):
        p  = item.get('price') or 0
        ps = 'inklusive' if p==0 else (money(p)+'/Mo.' if item.get('recurring') else money(p))
        rows.append([
            Paragraph(str(i), S['muted']),
            Paragraph(item.get('name',''), S['body']),
            Paragraph(item.get('cluster',''), S['muted']),
            Paragraph(ps, S['body']),
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
        ps      = 'inklusive' if p==0 else (money(p)+'/Mo.' if item.get('recurring') else money(p))

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
    t = Table([
        [Paragraph('<b>Einmalige Kosten</b>', S['h3']), Paragraph(f'<b>{money(one_time)}</b>', S['price'])],
        [Paragraph('<b>Monatliche Kosten</b>', S['h3']), Paragraph(f'<b>{money(monthly)}</b>',  S['price'])],
    ], colWidths=[CW-40*mm, 40*mm])
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
    if all_attachments:
        try:
            download_url = _dl.create_download_package(
                offer_no      = project.get('offerNo', 'ENTWURF'),
                all_attachments = all_attachments,
                pdf_bytes     = None,   # PDF noch nicht fertig hier
                pdf_filename  = filename,
            )
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

    return {'ok': True, 'download_url': f'/api/pdf/download/{filename}', 'package_url': download_url or ''}


def get_pdf_path(filename: str) -> str | None:
    path = os.path.join(EXPORT_DIR, filename)
    return path if os.path.exists(path) else None
