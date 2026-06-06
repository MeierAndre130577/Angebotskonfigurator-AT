"""
PDF-Generierung – Angebotskonfigurator Sielaff Austria v4
Deckblatt: Links weiß mit Logo + Infos, rechts Foto (konfigurierbar)
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

# ── Design Tokens ─────────────────────────────────────────────────────────────
RED   = colors.HexColor('#E30613')
DARK  = colors.HexColor('#1D1D1B')
MUTED = colors.HexColor('#71717a')
LINE  = colors.HexColor('#e4e4e7')
WHITE = colors.white
BG    = colors.HexColor('#f8f8f8')

W, H  = A4
MARGIN_L = 20*mm
MARGIN_R = 12*mm
MARGIN_T = 24*mm
MARGIN_B = 20*mm

EXPORT_DIR = os.path.join(os.path.dirname(__file__), 'exports')
os.makedirs(EXPORT_DIR, exist_ok=True)
LOGO_PATH = os.path.join(os.path.dirname(__file__), 'Logo_Sielaff.png')

def money(n):
    try:
        return f"€ {float(n):,.2f}".replace(',','X').replace('.', ',').replace('X','.')
    except:
        return "€ 0,00"

def fetch_image(url: str) -> io.BytesIO | None:
    if not url:
        return None
    try:
        r = httpx.get(url, timeout=10, follow_redirects=True)
        if r.status_code == 200:
            return io.BytesIO(r.content)
    except Exception:
        pass
    return None

# ── Deckblatt ─────────────────────────────────────────────────────────────────

def draw_cover(c: canvas.Canvas, data: dict):
    project  = data.get('project')  or {}
    provider = data.get('provider') or {}
    offer    = data.get('offer')    or []

    half = W / 2

    # ── Rechte Hälfte: Foto ───────────────────────────────────────────────────
    # cover_image_url kann in project['coverImage'] gesetzt werden
    cover_url = project.get('coverImage', '')

    # Fallback: erstes Optionsbild
    if not cover_url:
        for item in offer:
            if item.get('image_path'):
                cover_url = item['image_path']
                break

    cover_img = fetch_image(cover_url)

    if cover_img:
        try:
            c.drawImage(cover_img, half, 0, width=half, height=H,
                       preserveAspectRatio=False)
        except Exception:
            cover_img = None

    if not cover_img:
        # Fallback: Roter Hintergrund rechts
        c.setFillColor(RED)
        c.rect(half, 0, half, H, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont('Helvetica', 10)
        c.drawCentredString(half + half/2, H/2, 'Deckblatt-Foto wird')
        c.drawCentredString(half + half/2, H/2 - 12, 'in der Konfiguration festgelegt')

    # Dünner roter Streifen als Trenner
    c.setFillColor(RED)
    c.rect(half - 3, 0, 6, H, fill=1, stroke=0)

    # ── Linke Hälfte: Weiß ────────────────────────────────────────────────────
    c.setFillColor(WHITE)
    c.rect(0, 0, half - 3, H, fill=1, stroke=0)

    # Roter Balken oben links
    c.setFillColor(RED)
    c.rect(0, H - 18*mm, half - 3, 18*mm, fill=1, stroke=0)

    # Logo im roten Balken oben
    if os.path.exists(LOGO_PATH):
        try:
            logo_h = 12*mm
            logo_w = 12*mm
            c.drawImage(LOGO_PATH, 8*mm, H - 16*mm,
                       width=logo_w, height=logo_h,
                       preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # Firmenname im roten Balken
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 9)
    c.drawString(24*mm, H - 10*mm, provider.get('company', 'Sielaff Austria GmbH'))

    # Roter vertikaler Akzentstreifen links
    c.setFillColor(RED)
    c.rect(0, 0, 5*mm, H - 18*mm, fill=1, stroke=0)

    # ── Hauptinhalt links ─────────────────────────────────────────────────────
    content_x = 12*mm
    content_w = half - 20*mm

    # "ANGEBOT" Label
    c.setFillColor(RED)
    c.setFont('Helvetica-Bold', 8)
    c.drawString(content_x, H/2 + 40*mm, 'ANGEBOT')

    # Roter Unterstrich
    c.rect(content_x, H/2 + 37*mm, 20*mm, 1*mm, fill=1, stroke=0)

    # Kundenname groß
    c.setFillColor(DARK)
    c.setFont('Helvetica-Bold', 20)
    customer = project.get('customer', '')
    if len(customer) > 20:
        c.setFont('Helvetica-Bold', 15)
    c.drawString(content_x, H/2 + 24*mm, customer)

    # Projektname
    c.setFont('Helvetica', 13)
    c.setFillColor(MUTED)
    c.drawString(content_x, H/2 + 12*mm, project.get('project', ''))

    # Trennlinie
    c.setStrokeColor(LINE)
    c.setLineWidth(0.5)
    c.line(content_x, H/2 + 7*mm, half - 10*mm, H/2 + 7*mm)

    # Angebotsdaten
    c.setFillColor(DARK)
    c.setFont('Helvetica-Bold', 8)
    c.drawString(content_x, H/2 - 2*mm, 'Angebotsnummer')
    c.setFont('Helvetica', 8)
    c.setFillColor(MUTED)
    c.drawString(content_x, H/2 - 9*mm, project.get('offerNo', ''))

    c.setFillColor(DARK)
    c.setFont('Helvetica-Bold', 8)
    c.drawString(content_x, H/2 - 20*mm, 'Datum')
    c.setFont('Helvetica', 8)
    c.setFillColor(MUTED)
    c.drawString(content_x, H/2 - 27*mm, project.get('date', ''))

    c.setFillColor(DARK)
    c.setFont('Helvetica-Bold', 8)
    c.drawString(content_x, H/2 - 38*mm, 'Gültig bis')
    c.setFont('Helvetica', 8)
    c.setFillColor(MUTED)
    c.drawString(content_x, H/2 - 45*mm, project.get('valid', ''))

    # Kontaktdaten unten
    c.setStrokeColor(LINE)
    c.line(content_x, 35*mm, half - 10*mm, 35*mm)

    c.setFillColor(DARK)
    c.setFont('Helvetica-Bold', 8)
    c.drawString(content_x, 30*mm, project.get('contact', ''))
    c.setFont('Helvetica', 7.5)
    c.setFillColor(MUTED)
    c.drawString(content_x, 23*mm, project.get('customerEmail', ''))

    # Adresse Anbieter ganz unten
    c.setFont('Helvetica', 7)
    c.drawString(content_x, 12*mm, provider.get('address', ''))
    c.drawString(content_x, 7*mm, f"{provider.get('email','')}  ·  {provider.get('phone','')}")

    c.showPage()


# ── Kopf- und Fußzeile ────────────────────────────────────────────────────────

def make_canvas_class(project, provider):
    # Kopfzeile bündig mit rotem Streifen + 1cm tiefer
    HEADER_X = MARGIN_L          # bündig mit Überschriften (roter Strich)
    HEADER_Y = H - MARGIN_T - 5*mm  # 1cm tiefer

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

            # Kopfzeile – weißer Hintergrund
            header_h = 16*mm
            c.setFillColor(WHITE)
            c.rect(5*mm, H - header_h, W - 5*mm, header_h, fill=1, stroke=0)
            c.setStrokeColor(LINE)
            c.setLineWidth(0.5)
            c.line(HEADER_X, H - header_h, W - MARGIN_R, H - header_h)

            # Logo in Kopfzeile
            if os.path.exists(LOGO_PATH):
                try:
                    c.drawImage(LOGO_PATH, HEADER_X, H - header_h + 2*mm,
                               width=10*mm, height=10*mm,
                               preserveAspectRatio=True, mask='auto')
                except Exception:
                    pass

            # Firmenname
            c.setFillColor(DARK)
            c.setFont('Helvetica-Bold', 8)
            c.drawString(HEADER_X + 12*mm, HEADER_Y, provider.get('company', 'Sielaff Austria GmbH'))

            # Angebotsnummer Mitte
            c.setFont('Helvetica', 7.5)
            c.setFillColor(MUTED)
            offer_no = project.get('offerNo', '')
            c.drawCentredString(W/2, HEADER_Y, f'Angebot {offer_no}' if offer_no else '')

            # Datum rechts
            c.drawRightString(W - MARGIN_R, HEADER_Y, project.get('date', ''))

            # Fußzeile
            c.setStrokeColor(LINE)
            c.setLineWidth(0.5)
            c.line(MARGIN_L, 14*mm, W - MARGIN_R, 14*mm)
            addr = (f"{provider.get('company','')}  ·  {provider.get('address','')}  ·  "
                    f"{provider.get('email','')}  ·  {provider.get('phone','')}")
            c.setFont('Helvetica', 6.5)
            c.setFillColor(MUTED)
            c.drawString(MARGIN_L, 8*mm, addr)
            c.drawRightString(W - MARGIN_R, 8*mm, f'Seite {self._page_num + 1}')

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

    # Angebotsübersicht
    section_title(story, '1. Angebotsübersicht', S, CW)
    story.append(Paragraph(
        f"Kunde: <b>{project.get('customer','')}</b>  ·  "
        f"Projekt: <b>{project.get('project','')}</b>  ·  "
        f"Angebot: <b>{project.get('offerNo','')}</b>  ·  "
        f"Datum: <b>{project.get('date','')}</b>", S['body']))
    story.append(Spacer(1, 3*mm))

    hdr  = [Paragraph(x, S['muted']) for x in ['#','Option','Cluster','Preis']]
    rows = [hdr]
    for i, item in enumerate(offer, 1):
        p = item.get('price') or 0
        ps = 'inklusive' if p==0 else (money(p)+'/Mo.' if item.get('recurring') else money(p))
        rows.append([
            Paragraph(str(i), S['muted']),
            Paragraph(item.get('name',''), S['body']),
            Paragraph(item.get('cluster',''), S['muted']),
            Paragraph(ps, S['body']),
        ])
    t = Table(rows, colWidths=[10*mm, 95*mm, 38*mm, 32*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),BG),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('FONTSIZE',(0,0),(-1,0),7.5),
        ('LINEBELOW',(0,0),(-1,0),0.5,LINE),
        ('LINEBELOW',(0,1),(-1,-1),0.3,LINE),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
        ('ALIGN',(3,0),(3,-1),'RIGHT'),
    ]))
    story.append(t)
    story.append(PageBreak())

    # Detailseiten
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

        story.append(Spacer(1,2*mm))
        story.append(Paragraph(f"Preis: <b>{ps}</b>  ·  Cluster: {item.get('cluster','')}", S['muted']))
        story.append(Table([['']], colWidths=[CW],
            style=[('LINEBELOW',(0,0),(-1,-1),0.3,LINE),
                   ('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
        story.append(Spacer(1,4*mm))
    story.append(PageBreak())

    # Preiszusammenfassung
    section_title(story, '3. Preiszusammenfassung', S, CW)
    one_time = sum((i.get('price') or 0) for i in offer if not i.get('recurring'))
    monthly  = sum((i.get('price') or 0) for i in offer if i.get('recurring'))
    t = Table([
        [Paragraph('<b>Einmalige Kosten</b>', S['h3']), Paragraph(f'<b>{money(one_time)}</b>', S['price'])],
        [Paragraph('<b>Monatliche Kosten</b>', S['h3']), Paragraph(f'<b>{money(monthly)}</b>',  S['price'])],
    ], colWidths=[CW-40*mm, 40*mm])
    t.setStyle(TableStyle([
        ('LINEBELOW',(0,0),(-1,-1),0.5,LINE),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#fff1f2')),
    ]))
    story.append(t)
    story.append(Spacer(1,2*mm))
    story.append(Paragraph('Alle Preise verstehen sich exkl. gesetzlicher MwSt.', S['muted']))
    story.append(PageBreak())

    # Anlagen
    section_title(story, '4. Anlagen', S, CW)
    sel = [a for a in attachments if a.get('selected') or a.get('selected_default')]
    if sel:
        for a in sel:
            story.append(Paragraph(f"• {a.get('title','')}", S['body']))
            if a.get('description'):
                story.append(Paragraph(a['description'], S['muted']))
    else:
        story.append(Paragraph('Keine Anlagen ausgewählt.', S['muted']))
    story.append(PageBreak())

    # AGB
    section_title(story, '5. Rechtliche Hinweise', S, CW)
    agb = legal or (
        'Die ausgewiesenen Preise sind Nettopreise und verstehen sich zuzüglich der gesetzlichen '
        'Mehrwertsteuer. Die Distribution entscheidet Sielaff Austria GmbH. Es gelten die '
        'allgemeinen Geschäftsbedingungen der Sielaff Austria GmbH in der jeweils gültigen Fassung.'
    )
    for para in agb.split('\n'):
        if para.strip():
            story.append(Paragraph(para.strip(), S['body']))

    # Build
    doc.build(story, canvasmaker=MyCanvas)
    content_buf.seek(0)

    # Zusammenführen
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
