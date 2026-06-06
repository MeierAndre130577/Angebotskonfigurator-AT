"""
PDF-Generierung – Angebotskonfigurator Sielaff Austria
Struktur:
  Seite 1:  Deckblatt (Vollbild-Foto + Logo + Titel + Kunde + Datum)
  Seite 2:  Inhaltsverzeichnis
  Seite 3+: Angebotsübersicht
  Seite n+: Detailseiten pro Option
  Seite x:  Preiszusammenfassung
  Seite y:  Anlagen-Liste
  Seite z:  AGB / Rechtliche Hinweise
"""

import os, uuid, io, httpx
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Sielaff Design Tokens ─────────────────────────────────────────────────────
RED    = colors.HexColor('#E30613')
DARK   = colors.HexColor('#1D1D1B')
MUTED  = colors.HexColor('#71717a')
LINE   = colors.HexColor('#e4e4e7')
WHITE  = colors.white
BG     = colors.HexColor('#f8f8f8')

W, H   = A4   # 595 x 842 pt
MARGIN = 20 * mm
EXPORT_DIR = os.path.join(os.path.dirname(__file__), 'exports')
os.makedirs(EXPORT_DIR, exist_ok=True)

def money(n):
    try:
        return f"€ {float(n):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return "€ 0,00"

def fetch_image(url: str) -> io.BytesIO | None:
    """Bild von URL laden und als BytesIO zurückgeben"""
    if not url:
        return None
    try:
        r = httpx.get(url, timeout=10, follow_redirects=True)
        if r.status_code == 200:
            return io.BytesIO(r.content)
    except Exception:
        pass
    return None

# ── Kopf- und Fußzeile ────────────────────────────────────────────────────────

class HeaderFooterCanvas(canvas.Canvas):
    """Canvas mit Kopf- und Fußzeile auf allen Seiten außer Seite 1 (Deckblatt)"""

    def __init__(self, *args, meta=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.meta = meta or {}
        self._page_sections = []   # wird vom Dokument befüllt
        self._current_page  = 0

    def showPage(self):
        self._current_page += 1
        if self._current_page > 1:
            self._draw_header()
            self._draw_footer()
        super().showPage()

    def save(self):
        # letzte Seite
        self._current_page += 1
        if self._current_page > 1:
            self._draw_header()
            self._draw_footer()
        super().save()

    def _draw_header(self):
        """Kopfzeile: roter Balken links + Logo/Firmenname + Angebotsnummer + Datum"""
        c = self
        # Roter Seitenstreifen links
        c.setFillColor(RED)
        c.rect(0, 0, 6*mm, H, fill=1, stroke=0)

        # Kopfzeile Hintergrund
        c.setFillColor(WHITE)
        c.rect(6*mm, H - 18*mm, W - 6*mm, 18*mm, fill=1, stroke=0)

        # Trennlinie
        c.setStrokeColor(LINE)
        c.setLineWidth(0.5)
        c.line(6*mm, H - 18*mm, W, H - 18*mm)

        # Firmenname links
        c.setFillColor(DARK)
        c.setFont('Helvetica-Bold', 9)
        provider = self.meta.get('provider', {})
        c.drawString(14*mm, H - 11*mm, provider.get('company', 'Sielaff Austria GmbH'))

        # Angebotsnummer Mitte
        c.setFont('Helvetica', 8)
        c.setFillColor(MUTED)
        offer_no = self.meta.get('project', {}).get('offerNo', '')
        c.drawCentredString(W/2, H - 11*mm, f'Angebot {offer_no}' if offer_no else '')

        # Datum rechts
        date = self.meta.get('project', {}).get('date', '')
        c.drawRightString(W - 10*mm, H - 11*mm, date)

    def _draw_footer(self):
        """Fußzeile: Seitenzahl + Firmendaten + Seitenname"""
        c = self
        # Trennlinie
        c.setStrokeColor(LINE)
        c.setLineWidth(0.5)
        c.line(14*mm, 14*mm, W - 10*mm, 14*mm)

        provider = self.meta.get('provider', {})
        addr = f"{provider.get('company','Sielaff Austria GmbH')}  ·  {provider.get('address','')}  ·  {provider.get('email','')}  ·  {provider.get('phone','')}"

        c.setFont('Helvetica', 7)
        c.setFillColor(MUTED)
        c.drawString(14*mm, 8*mm, addr)
        c.drawRightString(W - 10*mm, 8*mm, f'Seite {self._current_page}')


# ── Deckblatt ─────────────────────────────────────────────────────────────────

def draw_cover(c: canvas.Canvas, data: dict):
    """Seite 1: Vollbild-Foto + Farbüberlagerung + Texte"""
    project  = data.get('project') or {}
    provider = data.get('provider') or {}
    offer    = data.get('offer') or []

    # Hintergrundfoto (erstes Optionsbild das vorhanden ist)
    cover_img = None
    for item in offer:
        img_data = fetch_image(item.get('image_path',''))
        if img_data:
            cover_img = img_data
            break

    if cover_img:
        try:
            c.drawImage(cover_img, 0, 0, width=W, height=H, preserveAspectRatio=False)
        except Exception:
            cover_img = None

    if not cover_img:
        # Fallback: roter Verlauf
        c.setFillColor(DARK)
        c.rect(0, 0, W, H, fill=1, stroke=0)

    # Dunkles Overlay für Lesbarkeit
    c.setFillAlpha(0.55)
    c.setFillColor(DARK)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillAlpha(1.0)

    # Roter Balken unten
    c.setFillColor(RED)
    c.rect(0, 0, W, 32*mm, fill=1, stroke=0)

    # Weißer Streifen links
    c.setFillColor(WHITE)
    c.setFillAlpha(0.15)
    c.rect(0, 0, 8*mm, H, fill=1, stroke=0)
    c.setFillAlpha(1.0)

    # Firmenname oben
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 13)
    c.drawString(18*mm, H - 28*mm, provider.get('company', 'Sielaff Austria GmbH'))

    # Roter Akzentstreifen
    c.setFillColor(RED)
    c.rect(18*mm, H - 33*mm, 40*mm, 1.5*mm, fill=1, stroke=0)

    # Angebotstitel groß
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 32)
    title = project.get('project') or 'Angebot'
    c.drawString(18*mm, H/2 + 10*mm, title)

    # Untertitel
    c.setFont('Helvetica', 14)
    c.setFillColor(colors.HexColor('#e4e4e7'))
    c.drawString(18*mm, H/2 - 5*mm, 'Produktkonfiguration & Preisübersicht')

    # Kundendaten unten links im roten Balken
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 10)
    c.drawString(18*mm, 20*mm, project.get('customer', ''))
    c.setFont('Helvetica', 9)
    c.drawString(18*mm, 13*mm, f"{project.get('contact','')}  ·  {project.get('customerEmail','')}")

    # Datum + Angebotsnummer rechts im roten Balken
    c.setFont('Helvetica-Bold', 9)
    c.drawRightString(W - 10*mm, 20*mm, f"Angebot {project.get('offerNo','')}")
    c.setFont('Helvetica', 9)
    c.drawRightString(W - 10*mm, 13*mm, f"Datum: {project.get('date','')}  ·  Gültig bis: {project.get('valid','')}")

    c.showPage()


# ── Styles ────────────────────────────────────────────────────────────────────

def get_styles():
    base = getSampleStyleSheet()
    styles = {
        'h1': ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=22, textColor=DARK, spaceAfter=6),
        'h2': ParagraphStyle('h2', fontName='Helvetica-Bold', fontSize=14, textColor=DARK, spaceAfter=4),
        'h3': ParagraphStyle('h3', fontName='Helvetica-Bold', fontSize=11, textColor=DARK, spaceAfter=3),
        'body': ParagraphStyle('body', fontName='Helvetica', fontSize=9, textColor=DARK, spaceAfter=4, leading=14),
        'muted': ParagraphStyle('muted', fontName='Helvetica', fontSize=8, textColor=MUTED, spaceAfter=3),
        'price': ParagraphStyle('price', fontName='Helvetica-Bold', fontSize=11, textColor=RED, alignment=TA_RIGHT),
        'toc_item': ParagraphStyle('toc_item', fontName='Helvetica', fontSize=10, textColor=DARK, spaceAfter=6),
        'toc_num': ParagraphStyle('toc_num', fontName='Helvetica-Bold', fontSize=10, textColor=RED, spaceAfter=6),
        'section_label': ParagraphStyle('section_label', fontName='Helvetica-Bold', fontSize=8,
                                         textColor=WHITE, alignment=TA_CENTER),
        'footer_addr': ParagraphStyle('footer_addr', fontName='Helvetica', fontSize=7, textColor=MUTED),
    }
    return styles


# ── Haupt-Generator ───────────────────────────────────────────────────────────

def generate_design_pdf(data: dict) -> dict:
    project     = data.get('project') or {}
    provider    = data.get('provider') or {}
    offer       = data.get('offer') or []
    attachments = data.get('attachments') or []
    legal       = data.get('legal_notice') or ''

    filename = f"Angebot_{project.get('offerNo','ENTWURF')}_{uuid.uuid4().hex[:6]}.pdf"
    filepath = os.path.join(EXPORT_DIR, filename)

    meta = {'project': project, 'provider': provider}

    # ── 1. Deckblatt mit eigenem Canvas ──────────────────────────────────────
    cover_buf = io.BytesIO()
    c_cover   = canvas.Canvas(cover_buf, pagesize=A4)
    draw_cover(c_cover, data)
    c_cover.save()
    cover_buf.seek(0)

    # ── 2. Restliche Seiten mit Platypus ─────────────────────────────────────
    content_buf = io.BytesIO()

    class MyCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._page_num = 1

        def showPage(self):
            self._draw_header_footer()
            self._page_num += 1
            super().showPage()

        def save(self):
            self._draw_header_footer()
            super().save()

        def _draw_header_footer(self):
            c = self
            # Roter Seitenstreifen links
            c.setFillColor(RED)
            c.rect(0, 0, 6*mm, H, fill=1, stroke=0)

            # Kopfzeile
            c.setFillColor(WHITE)
            c.rect(6*mm, H - 18*mm, W - 6*mm, 18*mm, fill=1, stroke=0)
            c.setStrokeColor(LINE)
            c.setLineWidth(0.5)
            c.line(6*mm, H - 18*mm, W, H - 18*mm)

            c.setFillColor(DARK)
            c.setFont('Helvetica-Bold', 9)
            c.drawString(14*mm, H - 11*mm, provider.get('company', 'Sielaff Austria GmbH'))

            c.setFont('Helvetica', 8)
            c.setFillColor(MUTED)
            offer_no = project.get('offerNo', '')
            c.drawCentredString(W/2, H - 11*mm, f'Angebot {offer_no}' if offer_no else '')
            c.drawRightString(W - 10*mm, H - 11*mm, project.get('date', ''))

            # Fußzeile
            c.setStrokeColor(LINE)
            c.line(14*mm, 14*mm, W - 10*mm, 14*mm)
            addr = f"{provider.get('company','')}  ·  {provider.get('address','')}  ·  {provider.get('email','')}  ·  {provider.get('phone','')}"
            c.setFont('Helvetica', 7)
            c.setFillColor(MUTED)
            c.drawString(14*mm, 8*mm, addr)
            c.drawRightString(W - 10*mm, 8*mm, f'Seite {self._page_num + 1}')  # +1 wegen Deckblatt

    doc = SimpleDocTemplate(
        content_buf,
        pagesize=A4,
        leftMargin=14*mm,
        rightMargin=10*mm,
        topMargin=22*mm,
        bottomMargin=20*mm,
    )

    S = get_styles()
    story = []

    def section_title(text):
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph(text, S['h1']))
        # Roter Unterstrich
        story.append(Table([['']], colWidths=[W - 24*mm],
            style=[('LINEBELOW', (0,0), (-1,-1), 1.5, RED), ('TOPPADDING',(0,0),(-1,-1),0), ('BOTTOMPADDING',(0,0),(-1,-1),3)]))
        story.append(Spacer(1, 4*mm))

    # ── Inhaltsverzeichnis ────────────────────────────────────────────────────
    section_title('Inhaltsverzeichnis')
    toc_items = [
        ('1', 'Angebotsübersicht'),
        ('2', 'Detailbeschreibungen'),
        ('3', 'Preiszusammenfassung'),
        ('4', 'Anlagen'),
        ('5', 'Rechtliche Hinweise'),
    ]
    for num, label in toc_items:
        row = [[Paragraph(f'{num}.', S['toc_num']), Paragraph(label, S['toc_item'])]]
        t = Table(row, colWidths=[12*mm, W - 36*mm])
        t.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LINEBELOW', (0,0), (-1,-1), 0.3, LINE),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t)
    story.append(PageBreak())

    # ── Angebotsübersicht ─────────────────────────────────────────────────────
    section_title('1. Angebotsübersicht')
    story.append(Paragraph(f"Kunde: <b>{project.get('customer','')}</b>  ·  Projekt: <b>{project.get('project','')}</b>", S['body']))
    story.append(Spacer(1, 4*mm))

    table_data = [[
        Paragraph('<b>Position</b>', S['body']),
        Paragraph('<b>Option</b>', S['body']),
        Paragraph('<b>Cluster</b>', S['body']),
        Paragraph('<b>Preis</b>', S['body']),
    ]]
    for i, item in enumerate(offer, 1):
        price_str = 'inklusive' if (item.get('price') or 0) == 0 else (
            money(item['price']) + '/Mo.' if item.get('recurring') else money(item['price'])
        )
        table_data.append([
            Paragraph(str(i), S['muted']),
            Paragraph(item.get('name',''), S['body']),
            Paragraph(item.get('cluster',''), S['muted']),
            Paragraph(price_str, S['body']),
        ])

    t = Table(table_data, colWidths=[12*mm, 90*mm, 40*mm, 35*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), BG),
        ('TEXTCOLOR',     (0,0), (-1,0), MUTED),
        ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,0), 8),
        ('LINEBELOW',     (0,0), (-1,0), 0.5, LINE),
        ('LINEBELOW',     (0,1), (-1,-1), 0.3, LINE),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('ALIGN',         (3,0), (3,-1), 'RIGHT'),
    ]))
    story.append(t)
    story.append(PageBreak())

    # ── Detailseiten ──────────────────────────────────────────────────────────
    section_title('2. Detailbeschreibungen')
    for i, item in enumerate(offer, 1):
        story.append(Paragraph(f"{i}. {item.get('name','')}", S['h2']))

        # Bild + Beschreibung nebeneinander
        img_data = fetch_image(item.get('image_path',''))
        desc = item.get('long_text') or item.get('short_text') or ''
        price_val = item.get('price') or 0
        price_str = 'inklusive' if price_val == 0 else (
            money(price_val) + ' / Monat' if item.get('recurring') else money(price_val)
        )

        if img_data:
            try:
                img = RLImage(img_data, width=55*mm, height=40*mm)
                row = [[img, Paragraph(desc, S['body'])]]
                t = Table(row, colWidths=[60*mm, W - 84*mm])
                t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(1,0),(1,0),8)]))
                story.append(t)
            except Exception:
                if desc:
                    story.append(Paragraph(desc, S['body']))
        else:
            if desc:
                story.append(Paragraph(desc, S['body']))

        story.append(Spacer(1, 2*mm))
        story.append(Paragraph(f"Preis: <b>{price_str}</b>  ·  Cluster: {item.get('cluster','')}", S['muted']))
        story.append(Table([['']], colWidths=[W - 24*mm],
            style=[('LINEBELOW',(0,0),(-1,-1),0.3,LINE),('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
        story.append(Spacer(1, 5*mm))

    story.append(PageBreak())

    # ── Preiszusammenfassung ──────────────────────────────────────────────────
    section_title('3. Preiszusammenfassung')
    one_time = sum((i.get('price') or 0) for i in offer if not i.get('recurring'))
    monthly  = sum((i.get('price') or 0) for i in offer if i.get('recurring'))

    summary_data = [
        [Paragraph('<b>Einmalige Kosten</b>', S['h3']), Paragraph(f'<b>{money(one_time)}</b>', S['price'])],
        [Paragraph('<b>Monatliche Kosten</b>', S['h3']), Paragraph(f'<b>{money(monthly)}</b>', S['price'])],
    ]
    t = Table(summary_data, colWidths=[W - 60*mm, 36*mm])
    t.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 0.5, LINE),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#fff1f2')),
    ]))
    story.append(t)
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph('Alle Preise verstehen sich exkl. gesetzlicher MwSt.', S['muted']))
    story.append(PageBreak())

    # ── Anlagen ───────────────────────────────────────────────────────────────
    section_title('4. Anlagen')
    sel_attachments = [a for a in attachments if a.get('selected') or a.get('selected_default')]
    if sel_attachments:
        for a in sel_attachments:
            story.append(Paragraph(f"• {a.get('title','')}", S['body']))
            if a.get('description'):
                story.append(Paragraph(a['description'], S['muted']))
    else:
        story.append(Paragraph('Keine Anlagen ausgewählt.', S['muted']))
    story.append(PageBreak())

    # ── AGB ───────────────────────────────────────────────────────────────────
    section_title('5. Rechtliche Hinweise')
    if legal:
        for para in legal.split('\n'):
            if para.strip():
                story.append(Paragraph(para.strip(), S['body']))
    else:
        story.append(Paragraph(
            'Die ausgewiesenen Preise sind Nettopreise und verstehen sich zuzüglich der gesetzlichen Mehrwertsteuer. '
            'Die Distribution entscheidet Sielaff Austria GmbH. Es gelten die allgemeinen Geschäftsbedingungen '
            'der Sielaff Austria GmbH in der jeweils gültigen Fassung.',
            S['body']
        ))

    # ── Build ─────────────────────────────────────────────────────────────────
    doc.build(story, canvasmaker=MyCanvas)
    content_buf.seek(0)

    # ── Deckblatt + Inhalt zusammenführen ─────────────────────────────────────
    try:
        from pypdf import PdfReader, PdfWriter
        writer = PdfWriter()
        for pdf_buf in [cover_buf, content_buf]:
            reader = PdfReader(pdf_buf)
            for page in reader.pages:
                writer.add_page(page)
        with open(filepath, 'wb') as f:
            writer.write(f)
    except Exception as e:
        # Fallback: nur Inhalt
        with open(filepath, 'wb') as f:
            f.write(content_buf.read())

    return {'ok': True, 'download_url': f'/api/pdf/download/{filename}'}


def get_pdf_path(filename: str) -> str | None:
    path = os.path.join(EXPORT_DIR, filename)
    return path if os.path.exists(path) else None
