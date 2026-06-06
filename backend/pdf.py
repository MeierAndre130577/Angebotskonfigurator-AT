"""
PDF-Generierung – Angebotskonfigurator Sielaff Austria v3
Deckblatt: Geteiltes Layout – linke Hälfte rot mit Logo, rechte Hälfte Foto
"""

import os, uuid, io, base64, httpx
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
MARGIN_L = 14*mm
MARGIN_R = 10*mm
MARGIN_T = 22*mm
MARGIN_B = 20*mm

EXPORT_DIR = os.path.join(os.path.dirname(__file__), 'exports')
os.makedirs(EXPORT_DIR, exist_ok=True)

# Logo-Pfad (wird beim Upload ins Backend-Verzeichnis gelegt)
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

# ── Deckblatt – Geteiltes Layout ──────────────────────────────────────────────

def draw_cover(c: canvas.Canvas, data: dict):
    project  = data.get('project') or {}
    provider = data.get('provider') or {}
    offer    = data.get('offer') or []

    half = W / 2

    # ── Linke Hälfte: Rot ────────────────────────────────────────────────────
    c.setFillColor(RED)
    c.rect(0, 0, half, H, fill=1, stroke=0)

    # Logo oben links
    if os.path.exists(LOGO_PATH):
        try:
            # Logo freistellen: weißes Rechteck hinter Logo (da Logo roten BG hat)
            logo_size = 38*mm
            logo_x = half/2 - logo_size/2
            logo_y = H - 55*mm
            c.drawImage(LOGO_PATH, logo_x, logo_y, width=logo_size, height=logo_size,
                       preserveAspectRatio=True, mask='auto')
        except Exception:
            # Fallback: Text
            c.setFillColor(WHITE)
            c.setFont('Helvetica-Bold', 22)
            c.drawCentredString(half/2, H - 40*mm, 'Sielaff')

    # Weißer Trennstrich zwischen Logo und Text
    c.setFillColor(WHITE)
    c.setFillAlpha(0.3)
    c.rect(half/2 - 20*mm, H - 62*mm, 40*mm, 0.5*mm, fill=1, stroke=0)
    c.setFillAlpha(1.0)

    # Firmenname unter Logo
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 11)
    c.drawCentredString(half/2, H - 72*mm, provider.get('company', 'Sielaff Austria GmbH'))

    # Angebotstitel groß in der Mitte links
    c.setFont('Helvetica-Bold', 9)
    c.setFillColor(colors.HexColor('#ffcccc'))
    c.drawCentredString(half/2, H/2 + 30*mm, 'ANGEBOT')

    # Kundenname groß
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 18)
    customer = project.get('customer', '')
    # Langer Name umbrechen
    if len(customer) > 18:
        c.setFont('Helvetica-Bold', 14)
    c.drawCentredString(half/2, H/2 + 14*mm, customer)

    # Projektname
    c.setFont('Helvetica', 11)
    c.setFillColor(colors.HexColor('#ffcccc'))
    proj_name = project.get('project', '')
    c.drawCentredString(half/2, H/2, proj_name)

    # Trennlinie
    c.setFillColor(WHITE)
    c.setFillAlpha(0.3)
    c.rect(half/2 - 25*mm, H/2 - 8*mm, 50*mm, 0.5*mm, fill=1, stroke=0)
    c.setFillAlpha(1.0)

    # Angebotsnummer + Datum unten links
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 8)
    c.drawCentredString(half/2, 40*mm, f"Angebot {project.get('offerNo','')}")
    c.setFont('Helvetica', 8)
    c.setFillColor(colors.HexColor('#ffcccc'))
    c.drawCentredString(half/2, 33*mm, f"Datum: {project.get('date','')}  ·  Gültig bis: {project.get('valid','')}")

    # Kontakt ganz unten
    c.setFont('Helvetica', 7)
    c.drawCentredString(half/2, 20*mm, provider.get('address',''))
    c.drawCentredString(half/2, 14*mm, f"{provider.get('email','')}  ·  {provider.get('phone','')}")

    # ── Rechte Hälfte: Foto ───────────────────────────────────────────────────
    # Foto des ersten Automaten mit Bild
    cover_img = None
    for item in offer:
        img_data = fetch_image(item.get('image_path',''))
        if img_data:
            cover_img = img_data
            break

    if cover_img:
        try:
            c.drawImage(cover_img, half, 0, width=half, height=H,
                       preserveAspectRatio=False)
            # Leichter dunkler Overlay für Eleganz
            c.setFillColor(DARK)
            c.setFillAlpha(0.15)
            c.rect(half, 0, half, H, fill=1, stroke=0)
            c.setFillAlpha(1.0)
        except Exception:
            cover_img = None

    if not cover_img:
        # Fallback: dunkelgrauer Hintergrund mit Muster
        c.setFillColor(colors.HexColor('#2d2d2d'))
        c.rect(half, 0, half, H, fill=1, stroke=0)
        # Dezentes Muster
        c.setFillColor(colors.HexColor('#3a3a3a'))
        for y in range(0, int(H), 40):
            c.rect(half, y, half, 20, fill=1, stroke=0)
        # Hinweistext
        c.setFillColor(MUTED)
        c.setFont('Helvetica', 9)
        c.drawCentredString(half + half/2, H/2, 'Produktfoto')

    # ── Vertikale Trennlinie ──────────────────────────────────────────────────
    c.setStrokeColor(WHITE)
    c.setLineWidth(2)
    c.setStrokeAlpha(0.3)
    c.line(half, 0, half, H)
    c.setStrokeAlpha(1.0)

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

            # Kopfzeile
            c.setFillColor(WHITE)
            c.rect(5*mm, H-17*mm, W-5*mm, 17*mm, fill=1, stroke=0)
            c.setStrokeColor(LINE)
            c.setLineWidth(0.5)
            c.line(5*mm, H-17*mm, W, H-17*mm)

            # Logo klein in Kopfzeile
            if os.path.exists(LOGO_PATH):
                try:
                    c.drawImage(LOGO_PATH, 7*mm, H-14*mm, width=10*mm, height=10*mm,
                               preserveAspectRatio=True, mask='auto')
                except Exception:
                    pass

            c.setFillColor(DARK)
            c.setFont('Helvetica-Bold', 8)
            c.drawString(20*mm, H-10*mm, provider.get('company','Sielaff Austria GmbH'))

            c.setFont('Helvetica', 7)
            c.setFillColor(MUTED)
            offer_no = project.get('offerNo','')
            c.drawCentredString(W/2, H-10*mm, f'Angebot {offer_no}' if offer_no else '')
            c.drawRightString(W-8*mm, H-10*mm, project.get('date',''))

            # Fußzeile
            c.setStrokeColor(LINE)
            c.line(14*mm, 14*mm, W-8*mm, 14*mm)
            addr = f"{provider.get('company','')}  ·  {provider.get('address','')}  ·  {provider.get('email','')}  ·  {provider.get('phone','')}"
            c.setFont('Helvetica', 6.5)
            c.setFillColor(MUTED)
            c.drawString(14*mm, 8*mm, addr)
            c.drawRightString(W-8*mm, 8*mm, f'Seite {self._page_num + 1}')

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

def section_title(story, text, S):
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(text, S['h1']))
    story.append(Table([['']], colWidths=[W - MARGIN_L - MARGIN_R],
        style=[('LINEBELOW',(0,0),(-1,-1),1.5,RED),
               ('TOPPADDING',(0,0),(-1,-1),0),
               ('BOTTOMPADDING',(0,0),(-1,-1),2)]))
    story.append(Spacer(1, 3*mm))


# ── Haupt-Generator ───────────────────────────────────────────────────────────

def generate_design_pdf(data: dict) -> dict:
    project     = data.get('project')     or {}
    provider    = data.get('provider')    or {}
    offer       = data.get('offer')       or []
    attachments = data.get('attachments') or []
    legal       = data.get('legal_notice') or ''

    # Deckblatt-Titel: "Angebot – Kundenname & Projektname"
    customer  = project.get('customer', '')
    proj_name = project.get('project', '')

    filename = f"Angebot_{project.get('offerNo','ENTWURF')}_{uuid.uuid4().hex[:6]}.pdf"
    filepath = os.path.join(EXPORT_DIR, filename)

    # ── 1. Deckblatt ─────────────────────────────────────────────────────────
    cover_buf = io.BytesIO()
    c_cover   = canvas.Canvas(cover_buf, pagesize=A4)
    draw_cover(c_cover, data)
    c_cover.save()
    cover_buf.seek(0)

    # ── 2. Inhalt ─────────────────────────────────────────────────────────────
    content_buf = io.BytesIO()
    MyCanvas    = make_canvas_class(project, provider)

    doc = SimpleDocTemplate(
        content_buf, pagesize=A4,
        leftMargin=MARGIN_L, rightMargin=MARGIN_R,
        topMargin=MARGIN_T,  bottomMargin=MARGIN_B,
    )

    S     = get_styles()
    story = []
    CW    = W - MARGIN_L - MARGIN_R  # Content Width

    # ── Inhaltsverzeichnis ────────────────────────────────────────────────────
    section_title(story, 'Inhaltsverzeichnis', S)
    toc = [('1','Angebotsübersicht'),('2','Detailbeschreibungen'),
           ('3','Preiszusammenfassung'),('4','Anlagen'),('5','Rechtliche Hinweise')]
    for num, label in toc:
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
    section_title(story, '1. Angebotsübersicht', S)
    story.append(Paragraph(
        f"Kunde: <b>{customer}</b>  ·  Projekt: <b>{proj_name}</b>  ·  "
        f"Angebot: <b>{project.get('offerNo','')}</b>  ·  Datum: <b>{project.get('date','')}</b>",
        S['body']))
    story.append(Spacer(1, 3*mm))

    hdr = [Paragraph(x, S['muted']) for x in ['#','Option','Cluster','Preis']]
    rows = [hdr]
    for i, item in enumerate(offer, 1):
        p = item.get('price') or 0
        price_str = 'inklusive' if p==0 else (money(p)+'/Mo.' if item.get('recurring') else money(p))
        rows.append([
            Paragraph(str(i), S['muted']),
            Paragraph(item.get('name',''), S['body']),
            Paragraph(item.get('cluster',''), S['muted']),
            Paragraph(price_str, S['body']),
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

    # ── Detailseiten ──────────────────────────────────────────────────────────
    section_title(story, '2. Detailbeschreibungen', S)

    for i, item in enumerate(offer, 1):
        display = (item.get('display_type') or '').strip()
        name    = item.get('name','')
        short   = item.get('short_text','') or ''
        long    = item.get('long_text','')  or ''
        p       = item.get('price') or 0
        price_s = 'inklusive' if p==0 else (money(p)+'/Mo.' if item.get('recurring') else money(p))

        story.append(Paragraph(f"{i}. {name}", S['h2']))

        img_data = fetch_image(item.get('image_path',''))

        # display_type Logik
        if display == 'Großes Bild + Beschreibung' or display == '':
            if img_data:
                try:
                    img = RLImage(img_data, width=CW, height=65*mm)
                    story.append(img)
                    story.append(Spacer(1,2*mm))
                except Exception:
                    pass
            if short: story.append(Paragraph(f"<b>{short}</b>", S['body']))
            if long:  story.append(Paragraph(long, S['body']))

        elif display == 'Kleines Bild + Langtext':
            desc_parts = []
            if short: desc_parts.append(Paragraph(f"<b>{short}</b>", S['body']))
            if long:  desc_parts.append(Paragraph(long, S['body']))
            if img_data and desc_parts:
                try:
                    img = RLImage(img_data, width=55*mm, height=40*mm)
                    t = Table([[img, desc_parts]], colWidths=[58*mm, CW-58*mm])
                    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(1,0),(1,0),8)]))
                    story.append(t)
                except Exception:
                    for p in desc_parts: story.append(p)
            else:
                for p in desc_parts: story.append(p)

        elif display == 'Kein Bild, Langtext + Kurztext':
            if long:  story.append(Paragraph(long, S['body']))
            if short: story.append(Paragraph(short, S['muted']))

        elif display == 'Kein Bild, Kurztext':
            if short: story.append(Paragraph(short, S['body']))

        else:
            # Fallback
            if short: story.append(Paragraph(short, S['body']))
            if long:  story.append(Paragraph(long, S['body']))

        story.append(Spacer(1,2*mm))
        story.append(Paragraph(f"Preis: <b>{price_s}</b>  ·  Cluster: {item.get('cluster','')}", S['muted']))
        story.append(Table([['']], colWidths=[CW],
            style=[('LINEBELOW',(0,0),(-1,-1),0.3,LINE),
                   ('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
        story.append(Spacer(1,4*mm))

    story.append(PageBreak())

    # ── Preiszusammenfassung ──────────────────────────────────────────────────
    section_title(story, '3. Preiszusammenfassung', S)
    one_time = sum((i.get('price') or 0) for i in offer if not i.get('recurring'))
    monthly  = sum((i.get('price') or 0) for i in offer if i.get('recurring'))

    t = Table([
        [Paragraph('<b>Einmalige Kosten</b>', S['h3']), Paragraph(f'<b>{money(one_time)}</b>', S['price'])],
        [Paragraph('<b>Monatliche Kosten</b>', S['h3']), Paragraph(f'<b>{money(monthly)}</b>', S['price'])],
    ], colWidths=[CW-38*mm, 38*mm])
    t.setStyle(TableStyle([
        ('LINEBELOW',(0,0),(-1,-1),0.5,LINE),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#fff1f2')),
    ]))
    story.append(t)
    story.append(Spacer(1,2*mm))
    story.append(Paragraph('Alle Preise verstehen sich exkl. gesetzlicher MwSt.', S['muted']))
    story.append(PageBreak())

    # ── Anlagen ───────────────────────────────────────────────────────────────
    section_title(story, '4. Anlagen', S)
    sel = [a for a in attachments if a.get('selected') or a.get('selected_default')]
    if sel:
        for a in sel:
            story.append(Paragraph(f"• {a.get('title','')}", S['body']))
            if a.get('description'):
                story.append(Paragraph(a['description'], S['muted']))
    else:
        story.append(Paragraph('Keine Anlagen ausgewählt.', S['muted']))
    story.append(PageBreak())

    # ── AGB ───────────────────────────────────────────────────────────────────
    section_title(story, '5. Rechtliche Hinweise', S)
    agb = legal or (
        'Die ausgewiesenen Preise sind Nettopreise und verstehen sich zuzüglich der gesetzlichen Mehrwertsteuer. '
        'Die Distribution entscheidet Sielaff Austria GmbH. Es gelten die allgemeinen Geschäftsbedingungen '
        'der Sielaff Austria GmbH in der jeweils gültigen Fassung.'
    )
    for para in agb.split('\n'):
        if para.strip():
            story.append(Paragraph(para.strip(), S['body']))

    # ── Build ─────────────────────────────────────────────────────────────────
    doc.build(story, canvasmaker=MyCanvas)
    content_buf.seek(0)

    # ── Zusammenführen ────────────────────────────────────────────────────────
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
