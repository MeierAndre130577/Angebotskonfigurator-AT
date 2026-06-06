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
HEADER_H   = 18*mm   # Höhe der Kopfzeile
MARGIN_L   = 20*mm
MARGIN_R   = 12*mm
MARGIN_T   = HEADER_H + 8*mm   # Inhalt startet UNTER der Kopfzeile
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

    # Roter Balken oben (volle Breite)
    c.setFillColor(RED)
    c.rect(0, H - 28*mm, W, 28*mm, fill=1, stroke=0)

    # Logo im roten Balken
    if os.path.exists(LOGO_PATH):
        try:
            c.drawImage(LOGO_PATH, MARGIN_L, H - 24*mm,
                       width=18*mm, height=18*mm,
                       preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # Firmenname im roten Balken
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 12)
    c.drawString(MARGIN_L + 22*mm, H - 12*mm,
                 provider.get('company', 'Sielaff Austria GmbH'))
    c.setFont('Helvetica', 8)
    c.setFillColor(colors.HexColor('#ffcccc'))
    c.drawString(MARGIN_L + 22*mm, H - 20*mm,
                 f"{provider.get('address','')}  ·  {provider.get('email','')}  ·  {provider.get('phone','')}")

    # Rechte Hälfte: Foto
    half = W / 2
    cover_url = project.get('coverImage', '')
    if not cover_url:
        for item in offer:
            if item.get('image_path'):
                cover_url = item['image_path']
                break

    cover_img = fetch_image(cover_url)
    if cover_img:
        try:
            img_y = H - 28*mm - 100*mm
            c.drawImage(cover_img, half, img_y,
                       width=half - 0, height=100*mm,
                       preserveAspectRatio=False)
            # Dezenter Rahmen
            c.setStrokeColor(LINE)
            c.setLineWidth(0.5)
            c.rect(half, img_y, half - 0, 100*mm, fill=0, stroke=1)
        except Exception:
            pass
    else:
        # Fallback: roter Platzhalter
        img_y = H - 28*mm - 100*mm
        c.setFillColor(colors.HexColor('#fff1f2'))
        c.rect(half, img_y, half, 100*mm, fill=1, stroke=0)
        c.setFillColor(MUTED)
        c.setFont('Helvetica', 9)
        c.drawCentredString(half + half/2, img_y + 48*mm, 'Deckblatt-Foto wird in der')
        c.drawCentredString(half + half/2, img_y + 40*mm, 'Konfiguration festgelegt')

    # Linke Seite: Angebotsinfos
    content_x = MARGIN_L
    text_top  = H - 28*mm - 15*mm

    # "ANGEBOT" Badge
    c.setFillColor(RED)
    c.setFont('Helvetica-Bold', 7)
    badge_w = 22*mm
    c.rect(content_x, text_top - 5*mm, badge_w, 6*mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.drawCentredString(content_x + badge_w/2, text_top - 2*mm, 'ANGEBOT')

    # Kundenname
    c.setFillColor(DARK)
    c.setFont('Helvetica-Bold', 22)
    customer = project.get('customer', '')
    if len(customer) > 18:
        c.setFont('Helvetica-Bold', 16)
    c.drawString(content_x, text_top - 20*mm, customer)

    # Projektname
    c.setFont('Helvetica', 13)
    c.setFillColor(MUTED)
    c.drawString(content_x, text_top - 30*mm, project.get('project', ''))

    # Trennlinie
    c.setStrokeColor(LINE)
    c.setLineWidth(0.8)
    c.line(content_x, text_top - 36*mm, half - 10*mm, text_top - 36*mm)

    # Details
    def detail_row(label, value, y):
        c.setFillColor(MUTED)
        c.setFont('Helvetica', 7.5)
        c.drawString(content_x, y + 4*mm, label)
        c.setFillColor(DARK)
        c.setFont('Helvetica-Bold', 9)
        c.drawString(content_x, y, value)

    detail_row('Angebotsnummer', project.get('offerNo','—'), text_top - 46*mm)
    detail_row('Datum',          project.get('date','—'),    text_top - 58*mm)
    detail_row('Gültig bis',     project.get('valid','—'),   text_top - 70*mm)
    detail_row('Ansprechpartner',project.get('contact','—'), text_top - 82*mm)

    # Roter Balken unten
    c.setFillColor(RED)
    c.rect(0, 0, W, 12*mm, fill=1, stroke=0)

    # Roter Seitenstreifen links
    c.setFillColor(RED)
    c.rect(0, 12*mm, 5*mm, H - 28*mm - 12*mm, fill=1, stroke=0)

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
