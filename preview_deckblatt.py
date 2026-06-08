"""
Deckblatt-Vorschau Generator
Erzeugt ein PNG-Bild das zeigt wie das Deckblatt aussehen wird.
Keine Verbindung zum Backend nötig – reines Designtool.
"""
from PIL import Image, ImageDraw, ImageFont
import math, sys

S = 2          # Auflösungs-Skalierung (2x = bessere Qualität)
PW = 595 * S   # Seitenbreite in Pixeln
PH = 842 * S   # Seitenhöhe in Pixeln

def p(pt):     return int(pt * S)          # PDF-Punkte → Pixel
def fy(y_pdf): return PH - p(y_pdf)        # PDF y (von unten) → PIL y (von oben)

# ── Farben ────────────────────────────────────────────────────────────────────
WHITE    = (255, 255, 255)
RED      = (227,   6,  19)
DARK     = ( 29,  29,  27)
GRAY_TRI = (208, 208, 208)   # graues Dreieck oben rechts
SHADOW   = (218, 218, 218)
ICON_BG  = (242, 242, 242)
LINE_C   = (224, 224, 224)
FOOTER_C = (226, 226, 226)
COVER_C  = (130, 160, 185)   # Platzhalter für Deckblatt-Foto (blaugrau)
MUTED    = ( 85,  85,  85)

FOOTER_H = 88   # Fußzeilenhöhe in PDF-Punkten

# ── Bogen-Parameter ───────────────────────────────────────────────────────────
# Bild ~1/3 Seitenbreite (~200pt), Bogen mit 80pt Schwung (deutlich sichtbar)
IMG_TOP_Y_PDF = 842 - 120   # Bild-Oberkante: 120pt vom oberen Seitenrand
ARCH_TOP_X    = 595 * 0.870  # 518pt – Bogen beginnt weit rechts oben & unten
ARCH_CP_X     = 595 * 0.595  # 354pt – linkster Punkt → 164pt Schwung!
ARCH_BOT_X    = 595 * 0.870  # 518pt – symmetrisch unten
ARCH_CP1_Y    = 842 * 0.780  # 657pt – sehr hoch → langer eleganter Einzug
ARCH_CP2_Y    = 842 * 0.220  # 185pt – sehr tief → langer eleganter Ausstieg

# ── Fonts ─────────────────────────────────────────────────────────────────────
FD = "C:/Windows/Fonts/"
try:
    F_TITLE  = ImageFont.truetype(FD + "times.ttf",   p(62))
    F_SUB    = ImageFont.truetype(FD + "arial.ttf",   p(12))
    F_LABEL  = ImageFont.truetype(FD + "arialbd.ttf", p(11))
    F_VAL    = ImageFont.truetype(FD + "arial.ttf",   p(11))
    F_FTR_B  = ImageFont.truetype(FD + "arialbd.ttf", p(8))
    F_FTR    = ImageFont.truetype(FD + "arial.ttf",   p(7))
    F_SLOGAN = ImageFont.truetype(FD + "arialbd.ttf", p(9))
except Exception as e:
    print(f"Font-Fehler (Fallback): {e}")
    F_TITLE = F_SUB = F_LABEL = F_VAL = F_FTR_B = F_FTR = F_SLOGAN = ImageFont.load_default()

# ── Bezier-Kurve berechnen ────────────────────────────────────────────────────
def cubic_bezier_pts(p0, p1, p2, p3, n=300):
    """Gibt n+1 Punkte auf der kubischen Bézierkurve zurück."""
    pts = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        x = u**3*p0[0] + 3*u**2*t*p1[0] + 3*u*t**2*p2[0] + t**3*p3[0]
        y = u**3*p0[1] + 3*u**2*t*p1[1] + 3*u*t**2*p2[1] + t**3*p3[1]
        pts.append((int(x), int(y)))
    return pts

# PIL-Koordinaten der Bogenpunkte (y-Achse umgekehrt!)
bp0 = (p(ARCH_TOP_X),  fy(IMG_TOP_Y_PDF))  # oben – Bogenbeginn bei Bild-Oberkante
bp1 = (p(ARCH_CP_X),   fy(ARCH_CP1_Y))     # Kontrollpunkt oben
bp2 = (p(ARCH_CP_X),   fy(ARCH_CP2_Y))     # Kontrollpunkt unten
bp3 = (p(ARCH_BOT_X),  fy(FOOTER_H))       # unten – bei Fußzeile

arch_curve = cubic_bezier_pts(bp0, bp1, bp2, bp3)

# ── Bild erzeugen ─────────────────────────────────────────────────────────────
img = Image.new('RGB', (PW, PH), WHITE)
d   = ImageDraw.Draw(img)

# 1. Deckblatt-Foto Platzhalter – von ARCH_CP_X aus (breit, liegt hinter weißer Maske)
d.rectangle([p(ARCH_CP_X), 0, PW, fy(FOOTER_H)], fill=COVER_C)
# Gitterlinien
for gx in range(p(ARCH_CP_X), PW, p(40)):
    d.line([(gx, 0), (gx, fy(FOOTER_H))], fill=(120,150,175), width=1)
for gy in range(0, fy(FOOTER_H), p(40)):
    d.line([(p(ARCH_CP_X), gy), (PW, gy)], fill=(120,150,175), width=1)
d.text((p(ARCH_TOP_X) + p(8), p(20)), "[ FOTO ]", fill=(200,220,235), font=F_LABEL)

# 2. Graues Dreieck oben rechts (dekorativ, über Bild-Oberkante)
tri = [
    (p(ARCH_TOP_X - 60), fy(842)),
    (PW,                  fy(842)),
    (PW,                  fy(IMG_TOP_Y_PDF + 20)),
]
d.polygon(tri, fill=GRAY_TRI)

# 3. Weiße Bogen-Maske (deckt linken Bereich ab – von ganz oben bis Fußzeile)
mask_poly = (
    [(0, 0)]                           # oben links Seite
    + [(p(ARCH_TOP_X), 0)]             # oben rechts bis Bogenbeginn
    + arch_curve                        # Bogen-Kurve
    + [(p(ARCH_BOT_X), fy(FOOTER_H))]  # Bogenende unten
    + [(0, fy(FOOTER_H))]              # links unten
)
d.polygon(mask_poly, fill=WHITE)

# Schatten hinter dem Bogen (dunkelgrau, leicht versetzt → Tiefenwirkung)
for i in range(len(arch_curve) - 1):
    d.line([(arch_curve[i][0]+p(3), arch_curve[i][1]),
            (arch_curve[i+1][0]+p(3), arch_curve[i+1][1])],
           fill=(180,180,180), width=p(5))
# Weißer Bogen-Strich (scharfe Kante)
for i in range(len(arch_curve) - 1):
    d.line([arch_curve[i], arch_curve[i+1]], fill=WHITE, width=p(4))

# 4. Logo oben links (roter Platzhalter)
LX, LY, LS = p(35), fy(842 - 40), p(56)
d.rectangle([LX, LY, LX + LS, LY + LS], fill=RED)
d.text((LX + p(6), LY + p(20)), "LOGO", fill=WHITE, font=F_LABEL)

# 5. ANGEBOT-Titel
# Times-Roman 62pt: Basislinie bei y=657 (PDF) = fy(657) in PIL
# Textoberkante ≈ Basislinie - Zeichenhöhe (ca. 44pt)
ang_top = fy(657) - p(44)
d.text((p(35), ang_top), "ANGEBOT", fill=DARK, font=F_TITLE)

# Rote Linie
rl_y = fy(640)
d.line([(p(35), rl_y), (p(93), rl_y)], fill=RED, width=p(2))

# Untertitel
sub_top = fy(616) - p(10)
d.text((p(35), sub_top), "Maßgeschneiderte Lösung für Ihr Vorhaben", fill=DARK, font=F_SUB)

# 6. Info-Box – vertikal zentriert, großzügiges Spacing
BX    = p(35)
BW    = p(int(ARCH_CP_X) - 35 - 20)   # passt in die weiße Fläche
ROW_H = p(52)                           # größerer Zeilenabstand (war 36)
BOX_H = ROW_H * 7 + p(24)
# Zentriert zwischen Untertitel-Ende (PDF y≈570) und Fußzeile+Rand (PDF y≈115)
MID_Y   = (570 + 115) // 2
BOX_TOP = fy(MID_Y) - BOX_H // 2

# Schatten
d.rounded_rectangle([BX + p(4), BOX_TOP + p(5), BX + BW + p(4), BOX_TOP + BOX_H + p(5)],
                     radius=p(8), fill=SHADOW)
# Weißer Kasten
d.rounded_rectangle([BX, BOX_TOP, BX + BW, BOX_TOP + BOX_H], radius=p(8), fill=WHITE)

rows = [
    ("Angebotsnummer", "ANG-2026-06-XXXXXX"),
    ("Datum",          "7.6.2026"),
    ("Kunde",          "Hubermüller GmbH"),
    ("Projekt",        "Messegespräch"),
    ("Ansprechpartner","Hans Huber"),
    ("Gültig bis",     "5.7.2026"),
    ("Version",        "1.0"),
]

for i, (lbl, val) in enumerate(rows):
    row_top = BOX_TOP + p(8) + i * ROW_H
    rcy     = row_top + ROW_H // 2

    # Icon-Kreis (größer)
    cx = BX + p(24)
    d.ellipse([cx - p(13), rcy - p(13), cx + p(13), rcy + p(13)], fill=ICON_BG)
    d.line([(cx - p(5), rcy), (cx + p(5), rcy)], fill=(136,136,136), width=p(2))
    d.line([(cx, rcy - p(5)), (cx, rcy + p(5))], fill=(136,136,136), width=p(2))

    # Label (fett)
    d.text((BX + p(46), rcy - p(8)), lbl, fill=DARK, font=F_LABEL)
    # Wert
    d.text((BX + p(175), rcy - p(8)), val, fill=DARK, font=F_VAL)

    # Trennlinie
    if i < 6:
        sy = row_top + ROW_H
        d.line([(BX + p(12), sy), (BX + BW - p(12), sy)], fill=LINE_C, width=1)

# 7. Fußzeile
FY = fy(FOOTER_H)   # Oberkante Fußzeile in PIL
d.rectangle([0, FY, PW, PH], fill=FOOTER_C)
d.line([(0, FY), (PW, FY)], fill=(204, 204, 204), width=1)

# Vertikale Trenner
d.line([(p(75), FY + p(12)), (p(75), PH - p(12))], fill=(187,187,187), width=1)
S2X = int(PW * 0.51)
d.line([(S2X, FY + p(12)), (S2X, PH - p(12))], fill=(187,187,187), width=1)

# Gebäude-Icon (vereinfacht)
bx, by = p(22), FY + p(14)
d.rectangle([bx, by, bx + p(30), by + p(40)], outline=(136,136,136), width=1)
d.rectangle([bx + p(10), by, bx + p(20), by + p(15)], outline=(136,136,136), width=1)

# Firmentext links
d.text((p(84), FY + p(14)), "Sielaff Austria GmbH", fill=DARK, font=F_FTR_B)
d.text((p(84), FY + p(26)), "Weissenbachweg 7,", fill=MUTED, font=F_FTR)
d.text((p(84), FY + p(37)), "AT-6067 Absam (Tirol)", fill=MUTED, font=F_FTR)

# Kontakt mitte
d.text((S2X + p(12), FY + p(14)), "0676/6570301", fill=MUTED, font=F_FTR)
d.text((S2X + p(12), FY + p(26)), "info@at.sielaff.com", fill=MUTED, font=F_FTR)
d.text((S2X + p(12), FY + p(37)), "www.sielaff.at", fill=MUTED, font=F_FTR)

# Slogan rechts
slogan = "Kompetent. Klar. Verlässlich."
bbox = d.textbbox((0, 0), slogan, font=F_SLOGAN)
sw = bbox[2] - bbox[0]
sx = PW - p(25) - sw
d.text((sx, FY + p(20)), slogan, fill=DARK, font=F_SLOGAN)
d.line([(sx, FY + p(34)), (PW - p(25), FY + p(34))], fill=RED, width=p(1))

# ── Speichern ─────────────────────────────────────────────────────────────────
import os
out = os.path.join(os.path.expanduser("~"), "deckblatt_vorschau.png")
img.save(out, dpi=(144, 144))
print(f"\nVorschau gespeichert: {out}")
print(f"  Groesse: {PW}x{PH}px  (entspricht A4 bei 144dpi)")
