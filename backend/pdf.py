"""
PDF-Generierung – Angebotskonfigurator Sielaff Austria v5
- Deckblatt: komplett weißes Design
- Kopfzeile: topMargin korrekt
- Summe in Angebotsübersicht
- Anlagen aus Optionsdokumenten (dedupliziert)
"""

import os, uuid, io, httpx
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, PageBreak, Image as RLImage)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

RED   = colors.HexColor('#E30613')
DARK  = colors.HexColor('#1D1D1B')
MUTED = colors.HexColor('#71717a')
LINE  = colors.HexColor('#e4e4e7')
WHITE = colors.white
BG    = colors.HexColor('#f8f8f8')

W, H       = A4
HEADER_H   = 26*mm   # Höhe der Kopfzeile (tiefer)
MARGIN_L   = 20*mm
MARGIN_R   = 12*mm
MARGIN_T   = HEADER_H + 13*mm  # Inhalt startet UNTER der Kopfzeile + 0.5cm extra
MARGIN_B   = 22*mm

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

def make_canvas_class(project, provider):
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

            # Logo
            if os.path.exists(LOGO_PATH):
                try:
                    c.drawImage(LOGO_PATH,
                               MARGIN_L,
                               H - HEADER_H + 2*mm,
                               width=12*mm, height=12*mm,
                               preserveAspectRatio=True, mask='auto')
                except Exception:
                    pass

            # Firmenname (bündig mit MARGIN_L + Logo-Breite)
            c.setFillColor(DARK)
            c.setFont('Helvetica-Bold', 8)
            c.drawString(MARGIN_L + 14*mm, H - HEADER_H/2 - 1*mm,
                        provider.get('company', 'Sielaff Austria GmbH'))

            # Angebotsnummer Mitte
            c.setFont('Helvetica', 7.5)
            c.setFillColor(MUTED)
            offer_no = project.get('offerNo', '')
            c.drawCentredString(W/2, H - HEADER_H/2 - 1*mm,
                               f'Angebot {offer_no}' if offer_no else '')

            # Datum rechts
            c.drawRightString(W - MARGIN_R, H - HEADER_H/2 - 1*mm,
                             project.get('date', ''))

            # Fußzeile
            c.setStrokeColor(LINE)
            c.line(MARGIN_L, MARGIN_B - 8*mm, W - MARGIN_R, MARGIN_B - 8*mm)
            addr = (f"{provider.get('company','')}  ·  {provider.get('address','')}  ·  "
                    f"{provider.get('email','')}  ·  {provider.get('phone','')}")
            c.setFont('Helvetica', 6.5)
            c.setFillColor(MUTED)
            c.drawString(MARGIN_L, MARGIN_B - 14*mm, addr)
            c.drawRightString(W - MARGIN_R, MARGIN_B - 14*mm,
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

    filename = f"Angebot_{project.get('offerNo','ENTWURF')}_{uuid.uuid4().hex[:6]}.pdf"
    filepath = os.path.join(EXPORT_DIR, filename)

    # ── Anlagen sammeln: aus Optionen + explizite Anlagen (dedupliziert) ──────
    all_attachments = []
    seen_titles = set()

    # Dokumente aus Optionen
    for item in offer:
        for doc in (item.get('documents') or []):
            title = doc.get('title', '').strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                all_attachments.append({**doc, '_from_option': item.get('name','')})

    # Explizite Anlagen
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
    MyCanvas    = make_canvas_class(project, provider)

    doc = SimpleDocTemplate(
        content_buf, pagesize=A4,
        leftMargin=MARGIN_L, rightMargin=MARGIN_R,
        topMargin=MARGIN_T,  bottomMargin=MARGIN_B,
    )

    S   = get_styles()
    CW  = W - MARGIN_L - MARGIN_R
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
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),BG),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('FONTSIZE',(0,0),(-1,0),7.5),
        ('LINEBELOW',(0,0),(-1,0),0.5,LINE),
        ('LINEBELOW',(0,1),(-1,-3),0.3,LINE),
        ('LINEABOVE',(0,-2),(-1,-1),0.8,RED),
        ('BACKGROUND',(0,-2),(-1,-1),colors.HexColor('#fff1f2')),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
        ('ALIGN',(3,0),(3,-1),'RIGHT'),
    ]))
    story.append(t)
    story.append(PageBreak())

    # ── Detailseiten ──────────────────────────────────────────────────────────
    section_title(story, '2. Detailbeschreibungen', S, CW)
    for i, item in enumerate(offer, 1):
        display = (item.get('display_type') or '').strip()
        name    = item.get('name','')
        short   = item.get('short_text','') or ''
        long_t  = item.get('long_text','')  or ''
        p       = item.get('price') or 0
        ps      = 'inklusive' if p==0 else (money(p)+'/Mo.' if item.get('recurring') else money(p))

        story.append(Paragraph(f"{i}. {name}", S['h2']))
        img_data = fetch_image(item.get('image_path',''))

        if display in ('Großes Bild + Beschreibung', ''):
            if img_data:
                try:
                    story.append(RLImage(img_data, width=CW, height=65*mm))
                    story.append(Spacer(1,2*mm))
                except Exception: pass
            if short: story.append(Paragraph(f"<b>{short}</b>", S['body']))
            if long_t: story.append(Paragraph(long_t, S['body']))

        elif display == 'Kleines Bild + Langtext':
            parts = []
            if short: parts.append(Paragraph(f"<b>{short}</b>", S['body']))
            if long_t: parts.append(Paragraph(long_t, S['body']))
            if img_data and parts:
                try:
                    img = RLImage(img_data, width=55*mm, height=40*mm)
                    t2  = Table([[img, parts]], colWidths=[58*mm, CW-58*mm])
                    t2.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(1,0),(1,0),8)]))
                    story.append(t2)
                except Exception:
                    for p2 in parts: story.append(p2)
            else:
                for p2 in parts: story.append(p2)

        elif display == 'Kein Bild, Langtext + Kurztext':
            if long_t: story.append(Paragraph(long_t, S['body']))
            if short:  story.append(Paragraph(short,  S['muted']))

        elif display == 'Kein Bild, Kurztext':
            if short: story.append(Paragraph(short, S['body']))
        else:
            if short:  story.append(Paragraph(short,  S['body']))
            if long_t: story.append(Paragraph(long_t, S['body']))

        # Dokumente der Option
        docs = item.get('documents') or []
        if docs:
            story.append(Spacer(1,1*mm))
            doc_names = ', '.join(d.get('title','') for d in docs if d.get('title'))
            story.append(Paragraph(f"Dokumente: {doc_names}", S['muted']))

        story.append(Spacer(1,2*mm))
        story.append(Paragraph(f"Preis: <b>{ps}</b>  ·  Cluster: {item.get('cluster','')}", S['muted']))
        story.append(Table([['']], colWidths=[CW],
            style=[('LINEBELOW',(0,0),(-1,-1),0.3,LINE),
                   ('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
        story.append(Spacer(1,4*mm))
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
    if all_attachments:
        for a in all_attachments:
            story.append(Paragraph(f"• <b>{a.get('title','')}</b>", S['body']))
            if a.get('description'):
                story.append(Paragraph(a['description'], S['muted']))
            if a.get('_from_option'):
                story.append(Paragraph(f"Zugehörig zu: {a['_from_option']}", S['muted']))
            story.append(Spacer(1, 1*mm))
    else:
        story.append(Paragraph('Keine Anlagen ausgewählt.', S['muted']))
    story.append(PageBreak())

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

    return {'ok': True, 'download_url': f'/api/pdf/download/{filename}'}


def get_pdf_path(filename: str) -> str | None:
    path = os.path.join(EXPORT_DIR, filename)
    return path if os.path.exists(path) else None
