# -*- coding: utf-8 -*-
"""Utilerías de dibujo (reportlab) para los planos."""
import math
from reportlab.lib import colors

NEGRO = colors.black
GRIS = colors.Color(.45, .45, .45)
GRIS_C = colors.Color(.72, .72, .72)
GRIS_MC = colors.Color(.88, .88, .88)
AZUL = colors.Color(0.0, 0.33, 0.80)
AZUL_C = colors.Color(.80, .90, 1.0)
ROJO = colors.Color(.85, .10, .10)
VERDE = colors.Color(0.0, 0.50, 0.20)
C30 = math.cos(math.radians(30))


class Vista:
    """Mapea metros del proyecto a mm del pliego."""
    def __init__(self, ox, oy, den):
        self.ox, self.oy, self.k = ox, oy, 1000.0 / den

    def p(self, x, y):
        return self.ox + x * self.k, self.oy + y * self.k


def lw(c, w):
    c.setLineWidth(w)


def texto(c, x, y, s, t=2.2, f='Helvetica', al='l', col=NEGRO, rot=0):
    c.saveState()
    c.setFillColor(col)
    c.setFont(f, t)
    c.translate(x, y)
    if rot:
        c.rotate(rot)
    if al == 'c':
        c.drawCentredString(0, 0, s)
    elif al == 'r':
        c.drawRightString(0, 0, s)
    else:
        c.drawString(0, 0, s)
    c.restoreState()


def rect_m(c, v, x0, y0, x1, y1, fill=None, stroke=NEGRO, w=0.18, dash=None):
    a = v.p(min(x0, x1), min(y0, y1))
    b = v.p(max(x0, x1), max(y0, y1))
    c.saveState()
    lw(c, w)
    if dash:
        c.setDash(list(dash), 0)
    if fill is not None:
        c.setFillColor(fill)
    if stroke is not None:
        c.setStrokeColor(stroke)
    c.rect(a[0], a[1], b[0] - a[0], b[1] - a[1],
           fill=1 if fill is not None else 0,
           stroke=1 if stroke is not None else 0)
    c.restoreState()


def linea_m(c, v, pts, w=0.18, col=NEGRO, dash=None):
    c.saveState()
    lw(c, w)
    c.setStrokeColor(col)
    if dash:
        c.setDash(list(dash), 0)
    p = c.beginPath()
    x, y = v.p(*pts[0])
    p.moveTo(x, y)
    for q in pts[1:]:
        x, y = v.p(*q)
        p.lineTo(x, y)
    c.drawPath(p, stroke=1, fill=0)
    c.restoreState()


def cota_h(c, v, x0, x1, y, off, txt=None, t=1.9):
    """Cota horizontal a la altura y, desplazada off (mm en pliego)."""
    a, b = v.p(x0, y), v.p(x1, y)
    yy = a[1] + off
    c.saveState()
    lw(c, 0.12)
    c.setStrokeColor(NEGRO)
    c.line(a[0], yy, b[0], yy)
    for xx in (a[0], b[0]):
        c.line(xx, a[1] + (1.0 if off > 0 else -1.0), xx, yy + (1.2 if off > 0 else -1.2))
        c.line(xx - 0.8, yy - 0.8, xx + 0.8, yy + 0.8)
    c.restoreState()
    s = txt if txt else '%.2f' % abs(x1 - x0)
    texto(c, (a[0] + b[0]) / 2, yy + 0.6, s, t, al='c')


def cota_v(c, v, y0, y1, x, off, txt=None, t=1.9):
    a, b = v.p(x, y0), v.p(x, y1)
    xx = a[0] + off
    c.saveState()
    lw(c, 0.12)
    c.line(xx, a[1], xx, b[1])
    for yy in (a[1], b[1]):
        c.line(a[0] + (1.0 if off > 0 else -1.0), yy, xx + (1.2 if off > 0 else -1.2), yy)
        c.line(xx - 0.8, yy - 0.8, xx + 0.8, yy + 0.8)
    c.restoreState()
    s = txt if txt else '%.2f' % abs(y1 - y0)
    texto(c, xx - 0.7, (a[1] + b[1]) / 2, s, t, al='c', rot=90)


def nivel_marca(c, x, y, txt, t=1.9, izq=False):
    """Marca de nivel (triángulo) en coordenadas de pliego."""
    c.saveState()
    lw(c, 0.15)
    p = c.beginPath()
    p.moveTo(x, y); p.lineTo(x - 1.3, y + 1.8); p.lineTo(x + 1.3, y + 1.8); p.close()
    c.drawPath(p, stroke=1, fill=0)
    c.line(x - 3, y, x + 14 if not izq else x + 3, y) if not izq else c.line(x - 14, y, x + 3, y)
    c.restoreState()
    if izq:
        texto(c, x - 14, y + 0.6, txt, t)
    else:
        texto(c, x + 2.0, y + 0.6, txt, t)


def norte(c, x, y, r=6):
    c.saveState()
    lw(c, 0.2)
    c.circle(x, y, r)
    p = c.beginPath()
    p.moveTo(x, y + r); p.lineTo(x - r * 0.35, y - r * 0.5); p.lineTo(x, y - r * 0.2); p.close()
    c.setFillColor(NEGRO)
    c.drawPath(p, stroke=1, fill=1)
    c.restoreState()
    texto(c, x, y + r + 1.5, 'N', 3, 'Helvetica-Bold', 'c')


def titulo_dibujo(c, x, y, txt, esc, t=3.6):
    texto(c, x, y, txt, t, 'Helvetica-Bold')
    w = c.stringWidth(txt, 'Helvetica-Bold', t)
    c.saveState(); lw(c, 0.5); c.line(x, y - 1.2, x + w, y - 1.2)
    lw(c, 0.15); c.line(x, y - 2.0, x + w, y - 2.0); c.restoreState()
    texto(c, x, y - 5.2, esc, 2.3)


def parrafo(c, x, y, lineas, t=2.2, inter=1.45, f='Helvetica', col=NEGRO):
    for s in lineas:
        bold = s.startswith('**')
        texto(c, x, y, s.strip('*'), t, 'Helvetica-Bold' if bold else f, col=col)
        y -= t * inter
    return y


def en_local(c, v, x, y, ang):
    c.saveState()
    px, py = v.p(x, y)
    c.translate(px, py)
    c.rotate(ang)
    c.scale(v.k, v.k)


def mueble(c, v, tipo, x, y, ang=0, col=NEGRO):
    """Muebles sanitarios / mobiliario en planta. (x,y) = punto contra muro,
    el mueble crece hacia +y local; ang gira (0: muro al sur)."""
    en_local(c, v, x, y, ang)
    c.setStrokeColor(col)
    c.setLineWidth(0.12 / v.k)
    if tipo == 'WC':
        c.rect(-0.25, 0, 0.5, 0.2)
        c.ellipse(-0.19, 0.18, 0.19, 0.68)
    elif tipo == 'LAV':
        c.rect(-0.28, 0, 0.56, 0.45)
        c.ellipse(-0.19, 0.07, 0.19, 0.37)
    elif tipo == 'REG':      # (x,y) = esquina; regadera 1.0 x 1.2
        pass
    elif tipo == 'FRE':
        c.rect(-0.45, 0, 0.9, 0.55)
        c.rect(-0.4, 0.06, 0.36, 0.42)
        c.rect(0.04, 0.06, 0.36, 0.42)
    elif tipo == 'EST':
        c.rect(-0.3, 0, 0.6, 0.6)
        for (a, b) in ((-0.14, 0.16), (0.14, 0.16), (-0.14, 0.44), (0.14, 0.44)):
            c.circle(a, b, 0.09)
    elif tipo == 'LDR':
        c.rect(-0.35, 0, 0.7, 0.6)
        for i in range(5):
            c.line(-0.25 + i * 0.1, 0.1, -0.25 + i * 0.1, 0.3)
        c.rect(-0.3, 0.33, 0.6, 0.22)
    elif tipo == 'LVD':
        c.rect(-0.3, 0, 0.6, 0.6)
        c.circle(0, 0.3, 0.2)
    elif tipo == 'CAL':
        c.circle(0, 0.25, 0.22)
        c.setFont('Helvetica', 0.14)
        c.drawCentredString(0, 0.2, 'CAL')
    elif tipo == 'CAMA':
        c.rect(-0.8, 0, 1.6, 2.0)
        c.rect(-0.7, 0.08, 0.6, 0.35)
        c.rect(0.1, 0.08, 0.6, 0.35)
        c.line(-0.8, 0.55, 0.8, 0.55)
    elif tipo == 'CAMA1':
        c.rect(-0.5, 0, 1.0, 1.9)
        c.rect(-0.38, 0.08, 0.76, 0.32)
        c.line(-0.5, 0.5, 0.5, 0.5)
    elif tipo == 'SOFA':
        c.rect(-1.1, 0, 2.2, 0.85)
        c.rect(-1.1, 0, 2.2, 0.25)
        c.rect(-1.1, 0, 0.22, 0.85)
        c.rect(0.88, 0, 0.22, 0.85)
    elif tipo == 'MESA':
        c.rect(-0.8, 0.45, 1.6, 0.9)
        for a in (-0.45, 0.0, 0.45):
            c.circle(a, 0.25, 0.17)
            c.circle(a, 1.55, 0.17)
    elif tipo == 'CLOSET':   # x,y esquina; dibuja en (0..L,0..0.6)
        pass
    c.restoreState()


def regadera(c, v, x0, y0, x1, y1, col=NEGRO):
    rect_m(c, v, x0, y0, x1, y1, stroke=col, w=0.12)
    linea_m(c, v, [(x0, y0), (x1, y1)], 0.08, col)
    linea_m(c, v, [(x0, y1), (x1, y0)], 0.08, col)
    cx, cy = v.p((x0 + x1) / 2, (y0 + y1) / 2)
    c.saveState(); c.setStrokeColor(col); lw(c, 0.12); c.circle(cx, cy, 0.05 * v.k); c.restoreState()


def closet(c, v, x0, y0, x1, y1, col=NEGRO):
    rect_m(c, v, x0, y0, x1, y1, stroke=col, w=0.1)
    linea_m(c, v, [(x0, y0), (x1, y1)], 0.06, col, dash=(1, 1))
    linea_m(c, v, [(x0, y1), (x1, y0)], 0.06, col, dash=(1, 1))


class Iso:
    def __init__(self, ox, oy, k, hl):
        self.ox, self.oy, self.k, self.hl = ox, oy, k, hl

    def p(self, x, y, z, lev=0):
        zi = lev * self.hl + z
        return (self.ox + (x - y) * C30 * self.k, self.oy + ((x + y) * 0.5 + zi) * self.k)


def iso_linea(c, I, pts, w=0.4, col=AZUL, dash=None):
    c.saveState(); lw(c, w); c.setStrokeColor(col)
    if dash:
        c.setDash(list(dash), 0)
    p = c.beginPath()
    a = I.p(*pts[0]); p.moveTo(*a)
    for q in pts[1:]:
        p.lineTo(*I.p(*q))
    c.drawPath(p, stroke=1, fill=0)
    c.restoreState()


def valvula(c, x, y, ang, col=AZUL, s=1.0):
    """Válvula de compuerta (moño) en coordenadas de pliego, eje según ang."""
    c.saveState(); c.translate(x, y); c.rotate(ang); c.setFillColor(col); c.setStrokeColor(col)
    lw(c, 0.15)
    p = c.beginPath()
    p.moveTo(-s, -s * 0.7); p.lineTo(s, s * 0.7); p.lineTo(s, -s * 0.7); p.lineTo(-s, s * 0.7); p.close()
    c.drawPath(p, fill=1, stroke=1)
    c.restoreState()


def medidor(c, x, y, col=AZUL, r=1.3):
    c.saveState(); c.setFillColor(colors.white); c.setStrokeColor(col); lw(c, 0.25)
    c.circle(x, y, r, fill=1, stroke=1); c.restoreState()
    texto(c, x, y - 0.55, 'M', 1.5, 'Helvetica-Bold', 'c', col)


def ang_iso(I, a, b):
    pa, pb = I.p(*a), I.p(*b)
    return math.degrees(math.atan2(pb[1] - pa[1], pb[0] - pa[0]))


def iso_caja(c, I, x0, y0, z0, x1, y1, z1, col=NEGRO, w=0.15, dash=None, ocultas=True):
    P = lambda x, y, z: (x, y, z)
    aristas = [
        ((x0, y0, z0), (x1, y0, z0)), ((x1, y0, z0), (x1, y1, z0)),
        ((x1, y1, z0), (x0, y1, z0)), ((x0, y1, z0), (x0, y0, z0)),
        ((x0, y0, z1), (x1, y0, z1)), ((x1, y0, z1), (x1, y1, z1)),
        ((x1, y1, z1), (x0, y1, z1)), ((x0, y1, z1), (x0, y0, z1)),
        ((x0, y0, z0), (x0, y0, z1)), ((x1, y0, z0), (x1, y0, z1)),
        ((x1, y1, z0), (x1, y1, z1)), ((x0, y1, z0), (x0, y1, z1)),
    ]
    for a, b in aristas:
        iso_linea(c, I, [a, b], w, col, dash)

