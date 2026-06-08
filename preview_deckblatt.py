"""
Deckblatt-Vorschau  –  Variante: Diagonaler Schnitt
Weiss links / Foto rechts / rote Akzentlinie
"""
from PIL import Image, ImageDraw, ImageFont
import os

S  = 2          # 2x Aufloesung
PW = 595 * S
PH = 842 * S

def p(pt):     return int(pt * S)
def fy(y):     return PH - p(y)    # PDF-y (unten=0) -> PIL-y (oben=0)

# ── Farben ────────────────────────────────────────────────────────────────────
WHITE    = (255, 255, 255)
RED      = (227,   6,  19)
DARK     = ( 29,  29,  27)
SHADOW   = (210, 210, 210)
ICON_BG  = (242, 242, 242)
LINE_C   = (224, 224, 224)
FOOTER_C = (232, 232, 232)
MUTED    = ( 90,  90,  90)
PHOTO_D  = ( 52,  72,  92)   # dunkles Foto
PHOTO_L  = ( 72,  96, 118)   # Gitter im Foto

# ── Layout-Konstanten ─────────────────────────────────────────────────────────
FOOTER_H  = 72          # Fusszeile hoeher = mehr Platz fuer Inhalt (PDF-pt)
MARGIN    = 38          # linker Rand

# Diagonale: oben bei x=DIAG_TOP, unten bei x=DIAG_BOT (PDF-pt)
DIAG_TOP  = 375         # oben rechts von Textbereich
DIAG_BOT  = 490         # unten weiter rechts -> dynamischer Schwung

# ── Fonts ─────────────────────────────────────────────────────────────────────
FD = "C:/Windows/Fonts/"
try:
    F_TITLE  = ImageFont.truetype(FD + "times.ttf",   p(58))
    F_SUB    = ImageFont.truetype(FD + "arial.ttf",   p(11))
    F_LABEL  = ImageFont.truetype(FD + "arialbd.ttf", p(10))
    F_VAL    = ImageFont.truetype(FD + "arial.ttf",   p(10))
    F_FTR_H  = ImageFont.truetype(FD + "arialbd.ttf", p(8))
    F_FTR    = ImageFont.truetype(FD + "arial.ttf",   p(7))
    F_SLOGAN = ImageFont.truetype(FD + "arialbd.ttf", p(8))
except Exception as e:
    print(f"Font-Fehler: {e}")
    F_TITLE = F_SUB = F_LABEL = F_VAL = F_FTR_H = F_FTR = F_SLOGAN = ImageFont.load_default()

# ── Info-Box Daten ────────────────────────────────────────────────────────────
rows = [
    ("Angebotsnummer", "ANG-2026-06-XXXXXX"),
    ("Datum",          "7.6.2026"),
    ("Kunde",          "Hubermueller GmbH"),
    ("Projekt",        "Messegespraech"),
    ("Ansprechpartner","Hans Huber"),
    ("Gueltig bis",    "5.7.2026"),
    ("Version",        "1.0"),
]

# ── Bild erzeugen ─────────────────────────────────────────────────────────────
img = Image.new('RGB', (PW, PH), WHITE)
d   = ImageDraw.Draw(img)

# ── 1. Foto-Hintergrund rechts ────────────────────────────────────────────────
d.rectangle([p(DIAG_TOP), 0, PW, fy(FOOTER_H)], fill=PHOTO_D)
step = p(50)
for gx in range(p(DIAG_TOP), PW, step):
    d.line([(gx,0),(gx,fy(FOOTER_H))], fill=PHOTO_L, width=1)
for gy in range(0, fy(FOOTER_H), step):
    d.line([(p(DIAG_TOP),gy),(PW,gy)], fill=PHOTO_L, width=1)
# "FOTO"-Label mittig im Bildbereich
foto_cx = (p(DIAG_TOP) + PW) // 2
foto_cy = PH // 2
d.text((foto_cx - p(20), foto_cy - p(6)), "[ FOTO ]", fill=(110,145,175), font=F_LABEL)

# ── 2. Weisses Trapez links ───────────────────────────────────────────────────
white_poly = [
    (0, 0),
    (p(DIAG_TOP), 0),
    (p(DIAG_BOT), fy(FOOTER_H)),
    (0, fy(FOOTER_H)),
]
d.polygon(white_poly, fill=WHITE)

# ── 3. Diagonale Akzentlinie ──────────────────────────────────────────────────
# Schatten (leicht versetzt)
d.line([(p(DIAG_TOP)+p(4), 0), (p(DIAG_BOT)+p(4), fy(FOOTER_H))],
       fill=(190,190,190), width=p(3))
# Rote Hauptlinie
d.line([(p(DIAG_TOP), 0), (p(DIAG_BOT), fy(FOOTER_H))],
       fill=RED, width=p(3))

# ── 4. Logo oben links ────────────────────────────────────────────────────────
#    38pt vom Rand, 35pt vom oberen Rand
LOGO_SIZE = p(52)
LX = p(MARGIN)
LY = p(35)
d.rectangle([LX, LY, LX+LOGO_SIZE, LY+LOGO_SIZE], fill=RED)
d.text((LX+p(7), LY+p(17)), "LOGO", fill=WHITE, font=F_LABEL)

# ── 5. ANGEBOT-Titel ──────────────────────────────────────────────────────────
#    Beginnt 50pt unter Logo-Unterkante → harmonischer Abstand
TITLE_TOP = LY + LOGO_SIZE + p(55)
d.text((p(MARGIN), TITLE_TOP), "ANGEBOT", fill=DARK, font=F_TITLE)

# Rote Dekorlinie (kurz, unter dem Titel)
LINE_Y = TITLE_TOP + p(58) + p(12)
d.line([(p(MARGIN), LINE_Y), (p(MARGIN+75), LINE_Y)], fill=RED, width=p(2))

# Untertitel
SUB_Y = LINE_Y + p(16)
d.text((p(MARGIN), SUB_Y), "Massgeschneiderte Loesung fuer Ihr Vorhaben",
       fill=MUTED, font=F_SUB)

# ── 6. Info-Box ───────────────────────────────────────────────────────────────
#    Vertikal zentriert zwischen Untertitel-Ende und Fusszeile
BX    = p(MARGIN)
BW    = p(310)          # passt sicher in die weisse Flaeche
ROW_H = p(48)
BOX_H = ROW_H * 7 + p(20)

# Mitte des freien Bereichs (in PIL-y)
CONTENT_TOP = SUB_Y + p(20)          # Ende des Untertitels + kleiner Puffer
CONTENT_BOT = fy(FOOTER_H) - p(10)  # direkt ueber Fusszeile
BOX_TOP = CONTENT_TOP + (CONTENT_BOT - CONTENT_TOP - BOX_H) // 2

# Kein Rahmen – Zeilen direkt auf weissem Hintergrund
# Symbole fuer jede Zeile (einfache Formen)
ICONS = ["#", "cal", "usr", "fldr", "usr", "clk", "tag"]

for i, (lbl, val) in enumerate(rows):
    row_top = BOX_TOP + i * ROW_H
    rcy     = row_top + ROW_H // 2
    cx      = BX + p(18)

    # Farbiger Icon-Kreis (roter Akzent)
    d.ellipse([cx-p(12), rcy-p(12), cx+p(12), rcy+p(12)], fill=(250, 235, 235))
    d.ellipse([cx-p(12), rcy-p(12), cx+p(12), rcy+p(12)], outline=RED, width=p(1))

    # Verschiedene einfache Symbole
    ic = ICONS[i]
    if ic == "#":   # Angebotsnummer – Raster
        for lx in [cx-p(4), cx+p(1)]:
            d.line([(lx, rcy-p(6)),(lx, rcy+p(6))], fill=RED, width=p(1))
        for ly in [rcy-p(2), rcy+p(3)]:
            d.line([(cx-p(7), ly),(cx+p(7), ly)], fill=RED, width=p(1))
    elif ic == "cal":  # Datum – Kalender
        d.rectangle([cx-p(7),rcy-p(7),cx+p(7),rcy+p(6)], outline=RED, width=p(1))
        d.line([(cx-p(7),rcy-p(3)),(cx+p(7),rcy-p(3))], fill=RED, width=p(1))
        d.line([(cx-p(3),rcy-p(9)),(cx-p(3),rcy-p(6))], fill=RED, width=p(1))
        d.line([(cx+p(3),rcy-p(9)),(cx+p(3),rcy-p(6))], fill=RED, width=p(1))
    elif ic == "usr":  # Person
        d.ellipse([cx-p(4),rcy-p(9),cx+p(4),rcy-p(1)], outline=RED, width=p(1))
        d.arc([cx-p(8),rcy-p(2),cx+p(8),rcy+p(8)], start=0, end=180, fill=RED, width=p(1))
    elif ic == "fldr":  # Ordner
        d.rectangle([cx-p(7),rcy-p(4),cx+p(7),rcy+p(6)], outline=RED, width=p(1))
        d.rectangle([cx-p(7),rcy-p(7),cx,rcy-p(4)], outline=RED, width=p(1))
    elif ic == "clk":  # Uhr
        d.ellipse([cx-p(8),rcy-p(8),cx+p(8),rcy+p(8)], outline=RED, width=p(1))
        d.line([(cx,rcy),(cx+p(5),rcy-p(4))], fill=RED, width=p(1))
        d.line([(cx,rcy),(cx,rcy-p(5))], fill=RED, width=p(1))
    else:  # Tag/Version
        d.rectangle([cx-p(6),rcy-p(6),cx+p(6),rcy+p(6)], outline=RED, width=p(1))
        d.ellipse([cx+p(2),rcy-p(2),cx+p(6),rcy+p(2)], fill=RED)

    # Label fett, Wert normal
    d.text((BX+p(36), rcy-p(7)), lbl,  fill=DARK, font=F_LABEL)
    d.text((BX+p(162), rcy-p(7)), val, fill=DARK, font=F_VAL)

# ── 7. Fusszeile ─────────────────────────────────────────────────────────────
#    2 Spalten: Firma+Adresse+UID  |  Kontakt
FY = fy(FOOTER_H)
d.rectangle([0, FY, PW, PH], fill=FOOTER_C)

# Obere rote Akzentlinie
d.line([(0, FY),(PW, FY)], fill=RED, width=p(2))

MID = PW // 2
# Trennlinie Mitte
d.line([(MID, FY+p(10)),(MID, PH-p(10))], fill=(200,200,200), width=1)

# Linke Spalte: Firma
CL = p(20)
d.text((CL, FY+p(10)), "Sielaff Austria GmbH",    fill=DARK,  font=F_FTR_H)
d.text((CL, FY+p(22)), "Weissenbachweg 7",         fill=MUTED, font=F_FTR)
d.text((CL, FY+p(32)), "AT-6067 Absam (Tirol)",    fill=MUTED, font=F_FTR)
d.text((CL, FY+p(44)), "UID: ATU-XXXXXXXX",        fill=MUTED, font=F_FTR)

# Rechte Spalte: Kontakt
CR = MID + p(20)
d.text((CR, FY+p(10)), "Kontakt",                  fill=DARK,  font=F_FTR_H)
d.text((CR, FY+p(22)), "Tel:   +43 676 6570301",   fill=MUTED, font=F_FTR)
d.text((CR, FY+p(32)), "Mail:  info@at.sielaff.com",fill=MUTED, font=F_FTR)
d.text((CR, FY+p(44)), "Web:   www.sielaff.at",    fill=MUTED, font=F_FTR)

# ── Speichern ─────────────────────────────────────────────────────────────────
out = os.path.join(os.path.expanduser("~"), "deckblatt_vorschau.png")
img.save(out, dpi=(144, 144))
print(f"Gespeichert: {out}")
