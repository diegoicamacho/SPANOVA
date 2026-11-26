# -*- coding: utf-8 -*-
"""
Juego de planos (PDF, A2 horizontal) de un edificio habitacional de
4 niveles con 4 departamentos por nivel (16 en total), cada uno con su
propio baño completo. Incluye instalación hidráulica de agua potable con
cisterna, equipo de bombeo, montantes e isométricos.

Sólo dibujo: no incluye memoria de cálculo.

Uso:  python3 generar_planos.py
"""
import os
import sys

from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dibujo import *  # noqa: F401,F403
from dibujo import (Vista, lw, texto, rect_m, linea_m, cota_h, cota_v, nivel_marca, norte,
                    titulo_dibujo, parrafo, mueble, regadera, closet, Iso, iso_linea, valvula,
                    medidor, ang_iso, iso_caja, NEGRO, GRIS, GRIS_C, GRIS_MC, AZUL, AZUL_C,
                    ROJO, VERDE)

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "Planos_Edificio_4_niveles_16_deptos.pdf")
SALIDA_DXF = os.path.join(AQUI, "Planos_Edificio_4_niveles_16_deptos.dxf")

PW, PH = 594.0, 420.0
FECHA = "Noviembre 2026"
H_NIVEL = 3.0
NIVELES = ["Planta Baja", "Nivel 1", "Nivel 2", "Nivel 3"]
NPT = ['±0.00', '+3.00', '+6.00', '+9.00']
ZP, ZPC = 2.60, 2.50          # plafón AF / AC

# Edificio: 16.00 x 19.00 m. Deptos de 8.00 x 7.50 m.
BX, BY = 16.0, 19.0
LOTE = (-2.5, -4.5, 18.5, 21.0)
APTS = ['A', 'B', 'C', 'D']    # A frente-poniente, B frente-oriente, C fondo-poniente, D fondo-oriente
NUM = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
TE, TI, TM = 0.25, 0.12, 0.20  # exterior, interior, medianero / núcleo

# Cisterna (interior) y cuarto de máquinas
CX0, CX1, CY0, CY1 = 6.0, 10.0, -3.8, -0.8
C_FONDO, C_AGUA = -2.80, -0.40
MAQ = (10.6, -4.0, 13.0, -0.6)
RIS_F = (8.0, 7.2)             # montante 1 (deptos A y B)
RIS_R = (8.0, 11.8)            # montante 2 (deptos C y D)


def M(apt, x, y):
    """Coordenadas del depto A -> depto apt (simetrías)."""
    if apt in ('B', 'D'):
        x = BX - x
    if apt in ('C', 'D'):
        y = BY - y
    return x, y


def depto_nombre(lev, apt):
    return '%d0%d' % (lev + 1, NUM[apt])


# ----------------------------------------------------------------------
#  MUROS
# ----------------------------------------------------------------------
def espejo_vanos_x(vanos, a, b):
    return [(a + b - vb, a + b - va, t, {'a': 'b', 'b': 'a'}.get(bi, bi), la)
            for (va, vb, t, bi, la) in vanos]


def muros_globales(nivel):
    pb = nivel == 0
    ventanas_frente = [(0.8, 3.6, 'V', None, 0), (5.2, 7.4, 'V', None, 0)]
    vf = ventanas_frente + espejo_vanos_x(ventanas_frente, 0, BX)
    lado = [(1.0, 3.5, 'V', None, 0), (5.0, 6.4, 'V', None, 0)]
    lado_r = [(BY - vb, BY - va, t, b, l) for (va, vb, t, b, l) in lado]
    acceso = [(8.2, 9.4, 'P', 'a', 1)] if pb else [(8.2, 9.4, 'V', None, 0)]
    W = [
        ('h', 0.0, 0.0, BX, TE, vf),
        ('h', BY, 0.0, BX, TE, vf),
        ('v', 0.0, 0.0, BY, TE, lado + acceso + lado_r),
        ('v', BX, 0.0, BY, TE, lado + [(8.2, 9.4, 'V', None, 0)] + lado_r),
        # deptos frente / pasillo
        ('h', 7.5, 0.0, BX, TM, [(3.2, 4.1, 'P', 'b', -1), (BX - 4.1, BX - 3.2, 'P', 'a', -1)]),
        ('h', 11.5, 0.0, BX, TM, [(3.2, 4.1, 'P', 'b', 1), (BX - 4.1, BX - 3.2, 'P', 'a', 1)]),
        # medianeros
        ('v', 8.0, 0.0, 6.9, TM, []),
        ('v', 8.0, 12.1, BY, TM, []),
        # ductos
        ('h', 6.9, 7.6, 8.4, TI, []), ('v', 7.6, 6.9, 7.5, TI, []), ('v', 8.4, 6.9, 7.5, TI, []),
        ('h', 12.1, 7.6, 8.4, TI, []), ('v', 7.6, 11.5, 12.1, TI, []), ('v', 8.4, 11.5, 12.1, TI, []),
        # escalera
        ('h', 10.1, 6.6, 10.7, TM, []),
        ('v', 10.7, 7.5, 10.1, TM, []),
    ]
    return W


# muros interiores del depto A (se reflejan para B, C, D)
MUROS_A = [
    ('v', 4.4, 0.0, 4.2, TI, []),
    ('h', 4.2, 4.4, 8.0, TI, [(4.55, 5.45, 'P', 'a', -1)]),
    ('v', 3.0, 5.6, 7.5, TI, []),
    ('h', 5.4, 4.4, 8.0, TI, [(4.5, 5.5, 'H', None, 0), (5.75, 6.45, 'P', 'a', 1)]),
    ('v', 4.4, 5.4, 7.5, TI, []),
    ('v', 5.6, 5.4, 7.5, TI, []),
]

CUARTOS_A = [  # nombre, x0, y0, x1, y1, punto de texto
    ('Sala - comedor', 0, 0, 4.4, 4.6, (2.6, 0.7)),
    ('Recámara', 4.4, 0, 8.0, 4.2, (5.6, 3.2)),
    ('Cocina', 0, 4.6, 3.0, 7.5, (1.5, 5.3)),
    ('Vestíbulo', 3.0, 4.6, 4.4, 7.5, (3.7, 6.2)),
    ('Lavado', 4.4, 5.4, 5.6, 7.5, (5.1, 5.75)),
    ('Baño', 5.6, 5.4, 8.0, 7.5, (6.9, 5.7)),
]


def tramos_muro(a, b, t, vanos):
    ext = t / 2
    res, ini = [], a - ext
    for (va, vb, *_r) in sorted(vanos):
        res.append((ini, va))
        ini = vb
    res.append((ini, b + ext))
    return [(u0, u1) for (u0, u1) in res if u1 - u0 > 1e-6]


def dibujar_muros(c, v, lista, col=NEGRO):
    for o, k, a, b, t, vanos in lista:
        for (u0, u1) in tramos_muro(a, b, t, vanos):
            if o == 'h':
                rect_m(c, v, u0, k - t / 2, u1, k + t / 2, fill=col, stroke=None)
            else:
                rect_m(c, v, k - t / 2, u0, k + t / 2, u1, fill=col, stroke=None)
        for (va, vb, tipo, bis, lado) in vanos:
            if tipo == 'V':
                if o == 'h':
                    rect_m(c, v, va, k - t / 2, vb, k + t / 2, stroke=col, w=0.12)
                    linea_m(c, v, [(va, k), (vb, k)], 0.12, col)
                else:
                    rect_m(c, v, k - t / 2, va, k + t / 2, vb, stroke=col, w=0.12)
                    linea_m(c, v, [(k, va), (k, vb)], 0.12, col)
            elif tipo == 'P':
                w = vb - va
                hx = va if bis == 'a' else vb
                R = w * v.k
                c.saveState(); lw(c, 0.25); c.setStrokeColor(col)
                if o == 'h':
                    cx, cy = v.p(hx, k)
                    hx2, hy2 = v.p(hx, k + lado * w)
                    st = {('a', 1): 0, ('a', -1): 270, ('b', 1): 90, ('b', -1): 180}[(bis, lado)]
                else:
                    cx, cy = v.p(k, hx)
                    hx2, hy2 = v.p(k + lado * w, hx)
                    st = {('a', 1): 0, ('a', -1): 90, ('b', 1): 270, ('b', -1): 180}[(bis, lado)]
                c.line(cx, cy, hx2, hy2)
                lw(c, 0.1)
                c.arc(cx - R, cy - R, cx + R, cy + R, st, 90)
                c.restoreState()


class Espejo:
    """Contexto que refleja el dibujo del depto A hacia B, C o D."""
    def __init__(self, c, v, apt):
        self.c, self.v, self.apt = c, v, apt

    def __enter__(self):
        c, v = self.c, self.v
        c.saveState()
        if self.apt in ('B', 'D'):
            px = v.p(BX / 2, 0)[0]
            c.translate(2 * px, 0); c.scale(-1, 1)
        if self.apt in ('C', 'D'):
            py = v.p(0, BY / 2)[1]
            c.translate(0, 2 * py); c.scale(1, -1)

    def __exit__(self, *a):
        self.c.restoreState()


def interior_A(c, v, modo):
    col = NEGRO if modo == 'arq' else GRIS_C
    colm = NEGRO if modo == 'arq' else GRIS
    dibujar_muros(c, v, MUROS_A, col)
    # baño completo
    regadera(c, v, 5.6, 6.3, 6.6, 7.5, colm)
    mueble(c, v, 'WC', 7.05, 7.5, 180, colm)
    mueble(c, v, 'LAV', 8.0, 5.95, 90, colm)
    # lavado
    mueble(c, v, 'LVD', 5.0, 7.5, 180, colm)
    px, py = v.p(4.65, 6.3)
    c.saveState(); lw(c, 0.12); c.setStrokeColor(colm); c.circle(px, py, 0.22 * v.k); c.restoreState()
    # cocina
    rect_m(c, v, 0.0, 6.9, 2.9, 7.5, stroke=colm, w=0.12)
    rect_m(c, v, 0.0, 4.9, 0.6, 6.9, stroke=colm, w=0.12)
    mueble(c, v, 'FRE', 1.3, 7.5, 180, colm)
    mueble(c, v, 'EST', 0.0, 5.9, -90, colm)
    if modo == 'arq':
        rect_m(c, v, 2.2, 6.85, 2.9, 7.5, stroke=colm, w=0.1)   # refri
        mueble(c, v, 'CAMA', 8.0, 2.0, 90)
        closet(c, v, 4.5, 0.3, 5.1, 2.2)
        mueble(c, v, 'SOFA', 0.0, 1.4, -90)
        mueble(c, v, 'MESA', 2.7, 2.6, 0)


def textos_deptos(c, v, lev, modo):
    for apt in APTS:
        for (nom, x0, y0, x1, y1, tp) in CUARTOS_A:
            px, py = v.p(*M(apt, *tp))
            if modo == 'arq':
                texto(c, px, py, nom, 1.7, 'Helvetica-Bold', 'c')
                if nom not in ('Vestíbulo', 'Lavado'):
                    texto(c, px, py - 2.2, '%.2f m²' % ((x1 - x0) * (y1 - y0)), 1.4, al='c')
            else:
                texto(c, px, py, nom, 1.5, al='c', col=GRIS)
        px, py = v.p(*M(apt, 4.65, 6.3))
        texto(c, px, py - 0.5, 'Cal.', 1.1, al='c', col=NEGRO if modo == 'arq' else GRIS)
        cx, cy = M(apt, 2.7, 1.95)
        px, py = v.p(cx, cy)
        texto(c, px, py, 'DEPTO. %s' % depto_nombre(lev, apt), 2.4, 'Helvetica-Bold', 'c',
              NEGRO if modo == 'arq' else GRIS)
        if modo == 'arq':
            texto(c, px, py - 2.8, '60.00 m²', 1.6, al='c')


def escalera(c, v, col=NEGRO):
    for i in range(10):
        x = 6.6 + i * 0.28
        linea_m(c, v, [(x, 7.6), (x, 8.8)], 0.1, col)
        linea_m(c, v, [(x, 8.9), (x, 10.0)], 0.1, col)
    rect_m(c, v, 6.6, 8.8, 9.12, 8.9, fill=col, stroke=None)
    linea_m(c, v, [(6.0, 8.2), (9.9, 8.2), (9.9, 9.45), (7.0, 9.45)], 0.12, col)
    a = v.p(7.0, 9.45)
    c.saveState(); c.setFillColor(col); p = c.beginPath()
    p.moveTo(a[0], a[1]); p.lineTo(a[0] + 1.6, a[1] + 0.7); p.lineTo(a[0] + 1.6, a[1] - 0.7)
    p.close(); c.drawPath(p, fill=1, stroke=0); c.restoreState()
    px, py = v.p(5.95, 8.05)
    texto(c, px, py - 0.6, 'SUBE', 1.4, al='c', col=col)


def planta(c, v, lev, modo='arq'):
    col = NEGRO if modo == 'arq' else GRIS_C
    colm = NEGRO if modo == 'arq' else GRIS
    dibujar_muros(c, v, muros_globales(lev), col)
    for apt in APTS:
        with Espejo(c, v, apt):
            interior_A(c, v, modo)
    escalera(c, v, colm)
    textos_deptos(c, v, lev, modo)
    for (tx, ty, s) in ((2.6, 9.3, 'Vestíbulo'), (13.4, 9.3, 'Vestíbulo'), (8.0, 10.75, 'Pasillo común'),
                        (8.0, 8.2, '')):
        px, py = v.p(tx, ty)
        texto(c, px, py, s, 1.8, 'Helvetica-Bold' if modo == 'arq' else 'Helvetica', 'c', colm)
    px, py = v.p(8.0, 9.55)
    texto(c, px, py, 'Escalera', 1.6, al='c', col=colm)
    for (sx, sy) in (RIS_F, RIS_R):
        px, py = v.p(sx, sy + (0.55 if sy > 9 else -0.6))
        texto(c, px, py, 'Ducto', 1.2, al='c', col=colm)
    px, py = v.p(2.6, 8.3)
    texto(c, px, py, 'N.P.T. ' + (NPT[lev] if modo == 'arq' and lev == 0 else
                                 ('±0.00' if lev == 0 else '+3.00 / +6.00 / +9.00')), 1.5, al='c', col=colm)


def exterior_pb(c, v, modo='arq'):
    col = NEGRO if modo == 'arq' else GRIS
    x0, y0, x1, y1 = LOTE
    rect_m(c, v, x0, y0, x1, y1, stroke=GRIS, w=0.2, dash=(4, 1, 1, 1))
    linea_m(c, v, [(x0, y0), (x1, y0)], 0.35, col)
    px, py = v.p(8.0, y0 - 2.1)
    texto(c, px, py, 'ALINEAMIENTO  —  CALLE', 2.0, 'Helvetica-Bold', 'c', col)
    rect_m(c, v, CX0 - 0.2, CY0 - 0.2, CX1 + 0.2, CY1 + 0.2, fill=GRIS_MC if modo == 'arq' else AZUL_C,
           stroke=col, w=0.25)
    rect_m(c, v, CX0, CY0, CX1, CY1, fill=colors.white, stroke=col, w=0.15)
    rect_m(c, v, 6.4, -3.4, 7.0, -2.8, stroke=col, w=0.15)
    linea_m(c, v, [(6.4, -3.4), (7.0, -2.8)], 0.08, col)
    linea_m(c, v, [(6.4, -2.8), (7.0, -3.4)], 0.08, col)
    rect_m(c, v, 9.3, -2.5, 9.7, -2.1, stroke=col, w=0.1, dash=(1, 0.8))
    px, py = v.p(8.0, -1.7)
    texto(c, px, py, 'CISTERNA', 2.0, 'Helvetica-Bold', 'c', col)
    texto(c, px, py - 2.4, '4.00 x 3.00 m', 1.6, al='c', col=col)
    rect_m(c, v, *MAQ, stroke=col, w=0.25)
    px, py = v.p((MAQ[0] + MAQ[2]) / 2, -3.5)
    texto(c, px, py, 'CTO. MÁQ.', 1.6, 'Helvetica-Bold', 'c', col)
    # andador de acceso
    linea_m(c, v, [(-1.25, y0 + 0.3), (-1.25, 8.8), (-0.3, 8.8)], 0.18, col)
    a = v.p(-0.3, 8.8)
    c.saveState(); c.setFillColor(col); p = c.beginPath()
    p.moveTo(a[0], a[1]); p.lineTo(a[0] - 1.6, a[1] + 0.7); p.lineTo(a[0] - 1.6, a[1] - 0.7); p.close()
    c.drawPath(p, fill=1, stroke=0); c.restoreState()
    px, py = v.p(-1.25, 3.0)
    texto(c, px - 0.8, py, 'ACCESO PEATONAL', 1.8, 'Helvetica-Bold', 'c', col, rot=90)
    px, py = v.p(17.25, 9.0)
    texto(c, px + 0.6, py, 'ANDADOR / JARDÍN', 1.6, al='c', col=col, rot=90)
    px, py = v.p(8.0, 20.1)
    texto(c, px, py, 'PATIO POSTERIOR', 1.7, al='c', col=col)


def cotas(c, v, pb):
    yb = LOTE[1] if pb else 0.0
    xs = [0, 4.4, 8.0, 11.6, 16.0]
    for a, b in zip(xs, xs[1:]):
        cota_h(c, v, a, b, yb, -7)
    if pb:
        cota_h(c, v, LOTE[0], 0, yb, -7)
        cota_h(c, v, 16.0, LOTE[2], yb, -7)
        cota_h(c, v, LOTE[0], LOTE[2], yb, -12, '%.2f' % (LOTE[2] - LOTE[0]))
    else:
        cota_h(c, v, 0, 16, yb, -12, '16.00')
    xr = LOTE[2] if pb else BX
    ys = [0, 4.2, 5.4, 7.5, 11.5, 13.6, 14.8, 19.0]
    for a, b in zip(ys, ys[1:]):
        cota_v(c, v, a, b, xr, 6)
    if pb:
        cota_v(c, v, LOTE[1], 0, xr, 6)
        cota_v(c, v, 19.0, LOTE[3], xr, 6)
        cota_v(c, v, LOTE[1], LOTE[3], xr, 11, '%.2f' % (LOTE[3] - LOTE[1]))
    else:
        cota_v(c, v, 0, 19, xr, 11, '19.00')


# ----------------------------------------------------------------------
#  MARCO
# ----------------------------------------------------------------------
TOTAL = 5


def marco(c, clave, nombre, escala, num):
    lw(c, 0.7); c.rect(10, 10, PW - 20, PH - 20)
    lw(c, 0.2); c.rect(12, 12, PW - 24, PH - 24)
    x0 = PW - 107
    lw(c, 0.5); c.line(x0, 12, x0, PH - 12)
    xm = x0 + 4
    y = PH - 22
    texto(c, xm, y, 'PROYECTO TIPO', 4.2, 'Helvetica-Bold'); y -= 6
    texto(c, xm, y, 'Edificio habitacional de 4 niveles', 3.0, 'Helvetica-Bold'); y -= 4.4
    texto(c, xm, y, '16 departamentos (4 por nivel)', 2.5); y -= 3.6
    texto(c, xm, y, 'Cada departamento con su propio baño completo', 2.5); y -= 3.6
    texto(c, xm, y, 'Agua potable: cisterna + equipo de bombeo', 2.5); y -= 5
    lw(c, 0.25); c.line(x0, y, PW - 12, y); y -= 5
    texto(c, xm, y, 'DATOS DEL PROYECTO', 2.6, 'Helvetica-Bold'); y -= 4
    y = parrafo(c, xm, y, [
        'Terreno: 21.00 x 25.50 m',
        'Desplante: 16.00 x 19.00 m',
        'Niveles: planta baja + 3 niveles = 4 pisos',
        'Departamentos: 4 por nivel = 16 en total',
        'Depto. tipo: 8.00 x 7.50 m = 60.00 m²',
        '  sala-comedor, cocina, 1 recámara,',
        '  1 baño completo (W.C., lavabo, regadera),',
        '  área de lavado',
        'Entrepiso: 3.00 m · altura a pretil 12.90 m',
    ], 2.15) - 2
    lw(c, 0.25); c.line(x0, y, PW - 12, y); y -= 5
    texto(c, xm, y, 'NOTAS GENERALES', 2.6, 'Helvetica-Bold'); y -= 4
    parrafo(c, xm, y, [
        '1. Cotas y niveles en metros.',
        '2. N.P.T. = nivel de piso terminado;',
        '    N.T.N. = nivel de terreno natural (±0.00).',
        '3. Numeración: Depto. 101-104 en P.B.,',
        '    201-204 en N1, 301-304 en N2, 401-404 en N3.',
        '4. Tubería de agua: cobre tipo M o PP-R.',
        '5. Proyecto tipo de referencia; adecuar al',
        '    reglamento local y al terreno real.',
    ], 2.05)
    yb = 92
    lw(c, 0.25); c.line(x0, yb, PW - 12, yb)
    texto(c, xm, yb - 5, 'CONTENIDO DE LA LÁMINA', 2.3, 'Helvetica-Bold')
    yy = yb - 10
    for s in nombre:
        texto(c, xm, yy, s, 3.0, 'Helvetica-Bold'); yy -= 4.4
    c.line(x0, 52, PW - 12, 52)
    texto(c, xm, 47, 'ESCALA', 2.0, col=GRIS)
    texto(c, xm, 42, escala, 3.0, 'Helvetica-Bold')
    texto(c, xm + 46, 47, 'ACOTACIONES', 2.0, col=GRIS)
    texto(c, xm + 46, 42, 'metros', 3.0, 'Helvetica-Bold')
    c.line(x0, 37, PW - 12, 37)
    texto(c, xm, 32, 'FECHA', 2.0, col=GRIS)
    texto(c, xm, 27.5, FECHA, 2.8, 'Helvetica-Bold')
    texto(c, xm + 46, 32, 'REVISÓ / D.R.O.', 2.0, col=GRIS)
    c.line(xm + 46, 22, PW - 16, 22)
    texto(c, xm, 15.5, 'Lámina %d de %d' % (num, TOTAL), 2.4)
    texto(c, PW - 16, 15.5, clave, 7.5, 'Helvetica-Bold', 'r')


# ----------------------------------------------------------------------
#  A-01  PLANTAS ARQUITECTÓNICAS
# ----------------------------------------------------------------------
def lamina_A01(c):
    marco(c, 'A-01', ['Plantas arquitectónicas', 'Planta baja', 'Planta tipo (N1 a N3)'], '1:100', 1)
    v1 = Vista(52, 100, 100)
    exterior_pb(c, v1)
    planta(c, v1, 0)
    cotas(c, v1, True)
    titulo_dibujo(c, 30, 25, 'PLANTA BAJA  ·  Deptos. 101 a 104', 'Esc. 1:100   N.P.T. ±0.00')
    v2 = Vista(290, 145, 100)
    planta(c, v2, 1)
    cotas(c, v2, False)
    titulo_dibujo(c, 280, 115, 'PLANTA TIPO  ·  Niveles 1, 2 y 3',
                  'Esc. 1:100   Deptos. 201-204, 301-304 y 401-404')
    norte(c, 470, 385)
    for vv, y0, y1 in ((v1, -5.2, 21.6), (v2, -1.2, 20.0)):
        linea_m(c, vv, [(6.2, y0), (6.2, y1)], 0.25, NEGRO, dash=(6, 1.5, 1, 1.5))
        for yy in (y0, y1):
            px, py = vv.p(6.2, yy)
            texto(c, px + 1.2, py + (0.8 if yy > 5 else -2.6), "A'" if yy > 5 else 'A', 2.8,
                  'Helvetica-Bold')
    # cuadro de departamentos
    y = 88
    texto(c, 280, y, 'CUADRO DE DEPARTAMENTOS', 2.5, 'Helvetica-Bold'); y -= 4.5
    filas = [('Nivel', 'Departamentos', 'Baños'),
             ('Planta Baja', '101, 102, 103, 104', '4'),
             ('Nivel 1', '201, 202, 203, 204', '4'),
             ('Nivel 2', '301, 302, 303, 304', '4'),
             ('Nivel 3', '401, 402, 403, 404', '4'),
             ('Total', '16 departamentos', '16')]
    for i, (a, b, cc) in enumerate(filas):
        f = 'Helvetica-Bold' if i in (0, len(filas) - 1) else 'Helvetica'
        texto(c, 282, y, a, 2.1, f); texto(c, 312, y, b, 2.1, f); texto(c, 372, y, cc, 2.1, f, 'r')
        c.saveState(); lw(c, 0.08); c.setStrokeColor(GRIS_C); c.line(280, y - 1, 374, y - 1); c.restoreState()
        y -= 3.6
    parrafo(c, 385, 88, [
        '**Departamento tipo (60.00 m²)',
        'Sala-comedor   20.24 m²',
        'Recámara         15.12 m²',
        'Cocina             8.70 m²',
        'Baño completo   5.04 m²',
        'Lavado / vestíbulo',
    ], 2.1)


# ----------------------------------------------------------------------
#  A-02  FACHADA Y CORTE
# ----------------------------------------------------------------------
def lamina_A02(c):
    marco(c, 'A-02', ['Fachada principal', "Corte A-A'"], '1:125', 2)
    v = Vista(42, 205, 125)
    linea_m(c, v, [(LOTE[0], 0), (LOTE[2], 0)], 0.5)
    for i in range(22):
        x = LOTE[0] + 0.2 + i * 0.95
        linea_m(c, v, [(x, 0), (x - 0.4, -0.4)], 0.08)
    rect_m(c, v, 0, 0, BX, 12.9, stroke=NEGRO, w=0.4)
    rect_m(c, v, 5.3, 12.9, 10.7, 14.7, stroke=GRIS, w=0.3)           # caseta (remetida)
    rect_m(c, v, 0, 12.9, BX, 13.05, fill=GRIS_C, stroke=NEGRO, w=0.15)
    for i in range(1, 5):
        rect_m(c, v, 0, i * 3.0 - 0.2, BX, i * 3.0, fill=GRIS_MC, stroke=NEGRO, w=0.12)
    rect_m(c, v, 7.9, 0, 8.1, 12.9, fill=GRIS_MC, stroke=NEGRO, w=0.1)  # junta / medianero
    for i in range(4):
        z = i * 3.0
        for (a, b, s) in ((0.8, 3.6, 0.9), (5.2, 7.4, 1.0), (BX - 3.6, BX - 0.8, 0.9), (BX - 7.4, BX - 5.2, 1.0)):
            rect_m(c, v, a, z + s, b, z + 2.4, fill=AZUL_C, stroke=NEGRO, w=0.25)
            n = max(2, int(round((b - a) / 1.1)))
            for k in range(1, n):
                xx = a + k * (b - a) / n
                linea_m(c, v, [(xx, z + s), (xx, z + 2.4)], 0.12)
            linea_m(c, v, [(a - 0.05, z + s), (b + 0.05, z + s)], 0.35)
    rect_m(c, v, *([MAQ[0], 0, MAQ[2], 2.2]), fill=GRIS_MC, stroke=NEGRO, w=0.3)
    rect_m(c, v, MAQ[0] + 0.5, 0, MAQ[0] + 1.3, 2.0, stroke=NEGRO, w=0.15)
    for k in range(4):
        linea_m(c, v, [(MAQ[0] + 0.5, 0.4 + k * 0.4), (MAQ[0] + 1.3, 0.4 + k * 0.4)], 0.06)
    rect_m(c, v, CX0 - 0.2, C_FONDO - 0.2, CX1 + 0.2, 0.15, stroke=GRIS, w=0.2, dash=(2, 1))
    px, py = v.p(8.0, -1.6)
    texto(c, px, py, 'Cisterna (oculta)', 1.6, al='c', col=GRIS)
    for i in range(4):
        px, py = v.p(2.2, i * 3.0 + 2.6)
        texto(c, px, py, 'Depto. %s' % depto_nombre(i, 'A'), 1.4, al='c', col=GRIS)
        px, py = v.p(BX - 2.2, i * 3.0 + 2.6)
        texto(c, px, py, 'Depto. %s' % depto_nombre(i, 'B'), 1.4, al='c', col=GRIS)
    for z, s in ((0, '±0.00 P.B.'), (3, '+3.00 N1'), (6, '+6.00 N2'), (9, '+9.00 N3'),
                 (12, '+12.00 Azotea'), (12.9, '+12.90 Pretil'), (14.7, '+14.70 Caseta')):
        px, py = v.p(LOTE[2], z)
        nivel_marca(c, px + 2, py, s, 1.7)
    for i in range(4):
        cota_v(c, v, i * 3.0, i * 3.0 + 3.0, LOTE[0], -4)
    cota_v(c, v, 12, 12.9, LOTE[0], -4)
    cota_v(c, v, 0, 12.9, LOTE[0], -9, '12.90')
    for a, b in ((0, 8), (8, 16)):
        cota_h(c, v, a, b, C_FONDO - 0.2, -5)
    cota_h(c, v, 0, 16, C_FONDO - 0.2, -10, '16.00')
    titulo_dibujo(c, 30, 146, 'FACHADA PRINCIPAL (SUR)', 'Esc. 1:125')

    # ---------------- corte A-A' (x = 6.20, viendo al poniente) ----------------
    v = Vista(270, 205, 125)
    Y0, Y1 = LOTE[1], LOTE[3]
    linea_m(c, v, [(Y0, 0), (CY0 - 0.2, 0)], 0.5)
    linea_m(c, v, [(CY1 + 0.2, 0), (Y1, 0)], 0.5)
    for i in range(28):
        y = Y0 + 0.3 + i * 0.95
        if CY0 - 0.4 < y < CY1 + 0.6:
            continue
        linea_m(c, v, [(y, 0), (y - 0.4, -0.4)], 0.08)
    rect_m(c, v, 0, -0.1, BY, 0.0, fill=GRIS, stroke=NEGRO, w=0.1)
    for i in range(1, 5):
        rect_m(c, v, -0.125, i * 3.0 - 0.2, BY + 0.125, i * 3.0, fill=GRIS, stroke=NEGRO, w=0.1)
    rect_m(c, v, -0.125, 12.0, 0.125, 12.9, fill=GRIS, stroke=NEGRO, w=0.1)
    rect_m(c, v, BY - 0.125, 12.0, BY + 0.125, 12.9, fill=GRIS, stroke=NEGRO, w=0.1)
    rect_m(c, v, 7.5, 12.0, 10.1, 14.7, stroke=NEGRO, w=0.25)          # caseta cortada
    rect_m(c, v, 7.5, 14.5, 10.1, 14.7, fill=GRIS, stroke=None)
    XC = 6.2
    # muros horizontales del nivel tipo que cruzan x = 6.2
    lista = list(muros_globales(1))
    for apt in APTS:
        for (o, k, a, b, t, vanos) in MUROS_A:
            if o != 'h':
                continue
            x0, y0 = M(apt, a, k); x1, _ = M(apt, b, k)
            vv = []
            for (va, vb, tp, bi, la) in vanos:
                p0, _ = M(apt, va, k); p1, _ = M(apt, vb, k)
                vv.append((min(p0, p1), max(p0, p1), tp, bi, la))
            lista.append(('h', y0, min(x0, x1), max(x0, x1), t, vv))
    for lev in range(4):
        z0 = lev * 3.0
        for (o, k, a, b, t, vanos) in lista:
            if o != 'h' or not (a - t / 2 <= XC <= b + t / 2):
                continue
            tipo = None
            for (va, vb, tp, bi, la) in vanos:
                if va <= XC <= vb:
                    tipo = tp
            segs = {None: [(z0, z0 + 2.8)], 'V': [(z0, z0 + 1.0), (z0 + 2.4, z0 + 2.8)],
                    'P': [(z0 + 2.1, z0 + 2.8)], 'H': [(z0 + 2.1, z0 + 2.8)]}[tipo]
            for (za, zb) in segs:
                rect_m(c, v, k - t / 2, za, k + t / 2, zb, fill=NEGRO, stroke=None)
            if tipo == 'V':
                rect_m(c, v, k - t / 2, z0 + 1.0, k + t / 2, z0 + 2.4, stroke=NEGRO, w=0.1)
        for (ym, s) in ((2.1, 'Recámara'), (4.8, 'Pas.'), (6.45, 'Baño'), (9.5, 'Vestíbulo'),
                        (12.55, 'Baño'), (14.2, 'Pas.'), (16.9, 'Recámara')):
            px, py = v.p(ym, z0 + 1.2)
            texto(c, px, py, s, 1.5, al='c')
        px, py = v.p(2.1, z0 + 0.5)
        texto(c, px, py, depto_nombre(lev, 'A'), 1.3, al='c', col=GRIS)
        px, py = v.p(16.9, z0 + 0.5)
        texto(c, px, py, depto_nombre(lev, 'C'), 1.3, al='c', col=GRIS)
        linea_m(c, v, [(0.15, z0 + 2.7), (BY - 0.15, z0 + 2.7)], 0.07, GRIS, dash=(1.5, 1))
    # escalera en elevación (detrás del corte)
    for lev in range(4):
        z0 = lev * 3.0
        linea_m(c, v, [(7.6, z0), (8.8, z0 + 1.5), (10.0, z0 + 1.5)], 0.15, GRIS)
        linea_m(c, v, [(8.9, z0 + 1.5), (10.0, z0 + 3.0)], 0.12, GRIS, dash=(1.2, 0.8))
    # cimentación
    for yy in (0.0, 4.2, 7.5, 11.5, 14.8, BY):
        rect_m(c, v, yy - 0.45, -0.9, yy + 0.45, -0.6, stroke=GRIS, w=0.15, dash=(1.5, 1))
        rect_m(c, v, yy - 0.1, -0.6, yy + 0.1, -0.1, stroke=GRIS, w=0.15, dash=(1.5, 1))
    # cisterna cortada
    rect_m(c, v, CY0 - 0.2, C_FONDO - 0.2, CY1 + 0.2, 0.15, fill=GRIS, stroke=NEGRO, w=0.15)
    rect_m(c, v, CY0, C_FONDO, CY1, 0.0, fill=colors.white, stroke=NEGRO, w=0.1)
    rect_m(c, v, CY0, C_FONDO, CY1, C_AGUA, fill=AZUL_C, stroke=None)
    linea_m(c, v, [(CY0, C_AGUA), (CY1, C_AGUA)], 0.2, AZUL)
    px, py = v.p((CY0 + CY1) / 2, -1.6)
    texto(c, px, py, 'CISTERNA', 1.8, 'Helvetica-Bold', 'c')
    # montantes (ocultos)
    linea_m(c, v, [(CY1 + 0.2, -0.3), (11.8, -0.3), (11.8, 11.6)], 0.3, AZUL, dash=(3, 1.2))
    linea_m(c, v, [(7.2, -0.3), (7.2, 11.6)], 0.3, AZUL, dash=(3, 1.2))
    px, py = v.p(7.05, 4.4)
    texto(c, px, py, 'Montante 1', 1.4, col=AZUL, rot=90)
    px, py = v.p(11.65, 4.4)
    texto(c, px, py, 'Montante 2', 1.4, col=AZUL, rot=90)
    for z, s in ((0, '±0.00'), (3, '+3.00'), (6, '+6.00'), (9, '+9.00'), (12, '+12.00'),
                 (12.9, '+12.90'), (14.7, '+14.70')):
        px, py = v.p(Y1, z)
        nivel_marca(c, px + 2, py, s, 1.7)
    for z, s in ((C_AGUA, 'N.A.M. %.2f' % C_AGUA), (C_FONDO, 'Fondo %.2f' % C_FONDO)):
        px, py = v.p(CY0 - 0.3, z)
        nivel_marca(c, px, py, s, 1.5, izq=True)
    for i in range(4):
        cota_v(c, v, i * 3.0, i * 3.0 + 3.0, BY, 5)
    cota_v(c, v, 0, 12.9, BY, 10, '12.90')
    for a, b in ((Y0, 0), (0, 7.5), (7.5, 11.5), (11.5, 19.0), (19.0, Y1)):
        cota_h(c, v, a, b, C_FONDO - 0.2, -5)
    px, py = v.p(Y0 + 0.4, 1.0)
    texto(c, px, py, 'Calle', 1.6)
    titulo_dibujo(c, 258, 146, "CORTE A-A'", 'Esc. 1:125   (por el eje x = 6.20: deptos. A y C, vestíbulo y cisterna)')


# ----------------------------------------------------------------------
#  RED DE AGUA (coordenadas del depto A, z sobre N.P.T.)
# ----------------------------------------------------------------------
# polilíneas de AF por plafón, y bajadas (x, y, z_salida, mueble)
AF_PLAFON = [
    [(7.45, 7.2), (7.05, 7.2), (6.1, 7.2), (5.0, 7.2), (4.65, 7.2), (1.1, 7.2)],
    [(7.45, 7.2), (7.45, 5.85), (7.75, 5.85)],
    [(4.65, 7.2), (4.65, 6.3)],
]
AF_BAJADAS = [(7.05, 7.2, 0.25, 'W.C.'), (6.1, 7.2, 1.10, 'Reg.'), (5.0, 7.2, 1.00, 'Lavad.'),
              (1.1, 7.2, 0.55, 'Freg.'), (7.75, 5.85, 0.55, 'Lav.'), (4.65, 6.3, 1.50, 'Cal.')]
AC_PLAFON = [
    [(4.65, 6.15), (6.1, 6.15), (6.1, 7.3)],
    [(6.1, 6.15), (7.75, 6.15), (7.75, 6.05)],
    [(4.65, 6.15), (1.5, 6.15), (1.5, 7.3)],
]
AC_BAJADAS = [(6.1, 7.3, 1.10), (7.75, 6.05, 0.55), (1.5, 7.3, 0.55)]
DIAM_A = [((7.45, 7.2), (7.05, 7.2), 'Ø19'), ((5.0, 7.2), (1.1, 7.2), 'Ø13'),
          ((7.05, 7.2), (6.1, 7.2), 'Ø19'), ((7.45, 7.2), (7.45, 5.85), 'Ø13'),
          ((6.1, 7.2), (5.0, 7.2), 'Ø19')]
DIAM_MONT = ['Ø38', 'Ø32', 'Ø25', 'Ø25']


def red_planta(c, v, rotular=True):
    for apt in APTS:
        for pl in AF_PLAFON:
            linea_m(c, v, [M(apt, *p) for p in pl], 0.45, AZUL)
        rx, ry = RIS_F if apt in 'AB' else RIS_R
        linea_m(c, v, [(rx, ry), M(apt, 7.45, 7.2)], 0.45, AZUL)
        for (x, y, z, s) in AF_BAJADAS:
            px, py = v.p(*M(apt, x, y))
            c.saveState(); c.setFillColor(AZUL); c.circle(px, py, 0.5, fill=1, stroke=0); c.restoreState()
        mx, my = M(apt, 7.7, 7.2)
        px, py = v.p(mx, my)
        c.saveState(); lw(c, 0.15); c.setStrokeColor(AZUL); c.setFillColor(colors.white)
        c.circle(px, py, 0.7, fill=1); c.restoreState()
        if rotular:
            for (a, b, s) in DIAM_A[:3]:
                pa, pb = v.p(*M(apt, *a)), v.p(*M(apt, *b))
                if abs(pa[1] - pb[1]) < 0.1:
                    texto(c, (pa[0] + pb[0]) / 2, pa[1] + (0.7 if apt in 'AB' else -2.2), s, 1.35,
                          'Helvetica-Bold', 'c', AZUL)
    for (rx, ry) in (RIS_F, RIS_R):
        px, py = v.p(rx, ry)
        c.saveState(); lw(c, 0.35); c.setStrokeColor(AZUL); c.setFillColor(colors.white)
        c.circle(px, py, 1.2, fill=1); c.setFillColor(AZUL); c.circle(px, py, 0.45, fill=1)
        c.restoreState()


def leyenda(c, x, y):
    texto(c, x, y, 'SIMBOLOGÍA', 2.6, 'Helvetica-Bold'); y -= 5
    items = [('lin', AZUL, None, 'Agua fría (AF) por plafón'),
             ('lin', AZUL, (3, 1), 'AF enterrada (bajo piso)'),
             ('lin', ROJO, (2, 1), 'Agua caliente (AC)'),
             ('lin', VERDE, None, 'Toma municipal / llenado de cisterna'),
             ('pto', AZUL, None, 'Salida a mueble'),
             ('sub', AZUL, None, 'Montante (subida de agua fría)'),
             ('med', AZUL, None, 'Llave de paso + medidor por depto.')]
    for tipo, col, dash, s in items:
        c.saveState(); c.setStrokeColor(col); c.setFillColor(col); lw(c, 0.5)
        if tipo == 'lin':
            if dash:
                c.setDash(list(dash), 0)
            c.line(x, y + 0.8, x + 10, y + 0.8)
        elif tipo == 'pto':
            c.circle(x + 5, y + 0.8, 0.6, fill=1, stroke=0)
        elif tipo == 'sub':
            lw(c, 0.3); c.circle(x + 5, y + 0.8, 1.2); c.circle(x + 5, y + 0.8, 0.45, fill=1)
        elif tipo == 'med':
            lw(c, 0.2); c.setFillColor(colors.white); c.circle(x + 5, y + 0.8, 1.0, fill=1)
        c.restoreState()
        texto(c, x + 13, y, s, 2.0)
        y -= 4.2
    return y


def lamina_IH01(c):
    marco(c, 'IH-01', ['Instalación hidráulica', 'Agua potable en planta', 'P.B. y planta tipo'], '1:100', 3)
    v1 = Vista(52, 100, 100)
    exterior_pb(c, v1, 'hid')
    planta(c, v1, 0, 'hid')
    red_planta(c, v1)
    # línea enterrada, equipo y toma
    linea_m(c, v1, [(11.8, -1.6), (11.8, -0.3), (8.0, -0.3), (8.0, RIS_R[1])], 0.6, AZUL, dash=(3, 1))
    linea_m(c, v1, [(9.5, -2.3), (11.0, -2.3)], 0.45, AZUL)
    for yy, nb in ((-3.0, 'B-1'), (-2.0, 'B-2')):
        px, py = v1.p(11.4, yy)
        c.saveState(); lw(c, 0.25); c.setStrokeColor(AZUL); c.circle(px, py, 2.6); c.restoreState()
        texto(c, px, py - 0.6, nb, 1.4, 'Helvetica-Bold', 'c', AZUL)
    linea_m(c, v1, [(11.0, -3.0), (11.0, -2.0)], 0.4, AZUL)
    linea_m(c, v1, [(11.8, -3.0), (11.8, -1.6)], 0.4, AZUL)
    px, py = v1.p(12.5, -1.4)
    c.saveState(); lw(c, 0.25); c.setStrokeColor(AZUL); c.circle(px, py, 1.6); c.restoreState()
    texto(c, px, py - 0.6, 'T', 1.4, 'Helvetica-Bold', 'c', AZUL)
    linea_m(c, v1, [(12.0, LOTE[1]), (12.0, -4.2), (9.6, -4.2), (9.6, -3.5)], 0.45, VERDE)
    px, py = v1.p(12.0, LOTE[1])
    c.saveState(); lw(c, 0.25); c.setStrokeColor(VERDE); c.rect(px - 1.6, py - 1.0, 3.2, 2.0); c.restoreState()
    texto(c, px + 2.4, py - 3.2, 'Toma municipal Ø25 + medidor', 1.6, 'Helvetica-Bold', col=VERDE)
    px, py = v1.p(8.0, 2.5)
    texto(c, px - 0.8, py, 'Línea enterrada Ø50', 1.5, 'Helvetica-Bold', 'c', AZUL, rot=90)
    cotas(c, v1, True)
    titulo_dibujo(c, 30, 25, 'INST. HIDRÁULICA  ·  PLANTA BAJA',
                  'Esc. 1:100   Cisterna, equipo de bombeo, línea a montantes y deptos. 101-104')
    v2 = Vista(290, 145, 100)
    planta(c, v2, 1, 'hid')
    red_planta(c, v2)
    for (rx, ry), s in ((RIS_F, 'MONTANTE 1'), (RIS_R, 'MONTANTE 2')):
        px, py = v2.p(rx, ry)
        texto(c, px, py + (2.0 if ry > 9 else -3.0), s, 1.5, 'Helvetica-Bold', 'c', AZUL)
    cotas(c, v2, False)
    titulo_dibujo(c, 280, 115, 'INST. HIDRÁULICA  ·  PLANTA TIPO',
                  'Esc. 1:100   Niveles 1, 2 y 3 (red idéntica en los tres niveles)')
    y = leyenda(c, 380, 392)
    parrafo(c, 280, 92, [
        '**Notas',
        '1. Montante 1 alimenta los deptos. A y B (x01, x02); montante 2 los deptos. C y D (x03, x04).',
        '2. Cada departamento tiene en el ducto su llave de paso y medidor; la red interior corre por',
        '    plafón y baja a cada mueble ahogada en muro.',
        '3. Alturas de salidas sobre N.P.T.: W.C. 0.25 · lavabo y fregadero 0.55 · lavadora 1.00 ·',
        '    mezcladora de regadera 1.10 · calentador 1.50.',
        '4. Agua caliente con calentador eléctrico de paso en el área de lavado (ver IH-03).',
        '5. Diámetros en mm: 13 = 1/2"  19 = 3/4"  25 = 1"  32 = 1 1/4"  38 = 1 1/2"  50 = 2"',
    ], 2.0)


# ----------------------------------------------------------------------
#  ISOMÉTRICOS
# ----------------------------------------------------------------------
def poly_iso(c, I, pts, w=0.45, col=AZUL, dash=None):
    iso_linea(c, I, pts, w, col, dash)


def rot_iso(c, I, a, b, s, t=1.6, col=AZUL, abajo=False):
    pa, pb = I.p(*a), I.p(*b)
    ang = ang_iso(I, a, b)
    if ang > 90:
        ang -= 180
    if ang < -90:
        ang += 180
    c.saveState(); c.translate((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2); c.rotate(ang)
    texto(c, 0, -2.2 if abajo else 0.6, s, t, 'Helvetica-Bold', 'c', col)
    c.restoreState()


def red_depto_iso(c, I, apt, lev, rot=False, t=1.6, ac=False, z_riser=True):
    rx, ry = RIS_F if apt in 'AB' else RIS_R
    a0 = M(apt, 7.45, 7.2)
    poly_iso(c, I, [(rx, ry, ZP, lev), (a0[0], a0[1], ZP, lev)], 0.45)
    pa, pb = I.p(rx, ry, ZP, lev), I.p(a0[0], a0[1], ZP, lev)
    ang = ang_iso(I, (rx, ry, ZP, lev), (a0[0], a0[1], ZP, lev))
    medidor(c, pa[0] + (pb[0] - pa[0]) * 0.55, pa[1] + (pb[1] - pa[1]) * 0.55, AZUL, 0.9 if not rot else 1.1)
    for pl in AF_PLAFON:
        poly_iso(c, I, [(*M(apt, *p), ZP, lev) for p in pl], 0.45)
    for (x, y, z, s) in AF_BAJADAS:
        X, Y = M(apt, x, y)
        poly_iso(c, I, [(X, Y, ZP, lev), (X, Y, z, lev)], 0.4)
        q = I.p(X, Y, z, lev)
        c.saveState(); c.setFillColor(AZUL); c.circle(q[0], q[1], 0.45, fill=1, stroke=0); c.restoreState()
        if rot:
            texto(c, q[0], q[1] - 2.3, s, t * 0.95, al='c')
    if rot:
        for (a, b, s) in DIAM_A:
            rot_iso(c, I, (*M(apt, *a), ZP, lev), (*M(apt, *b), ZP, lev), s, t)
        rot_iso(c, I, (rx, ry, ZP, lev), (a0[0], a0[1], ZP, lev), 'Ø19', t, abajo=True)
    if ac:
        for pl in AC_PLAFON:
            poly_iso(c, I, [(*M(apt, *p), ZPC, lev) for p in pl], 0.45, ROJO, (2, 1))
        X, Y = M(apt, 4.65, 6.15)
        poly_iso(c, I, [(X, Y, 1.6, lev), (X, Y, ZPC, lev)], 0.45, ROJO, (2, 1))
        for (x, y, z) in AC_BAJADAS:
            X, Y = M(apt, x, y)
            poly_iso(c, I, [(X, Y, ZPC, lev), (X, Y, z, lev)], 0.4, ROJO, (2, 1))
            q = I.p(X, Y, z, lev)
            c.saveState(); c.setFillColor(ROJO); c.circle(q[0], q[1], 0.45, fill=1, stroke=0); c.restoreState()


def iso_cisterna(c, I, det):
    t = 1.9
    iso_caja(c, I, CX0, CY0, C_FONDO, CX1, CY1, 0.0, NEGRO, 0.2)
    pa = [I.p(CX0, CY0, C_AGUA), I.p(CX1, CY0, C_AGUA), I.p(CX1, CY1, C_AGUA), I.p(CX0, CY1, C_AGUA)]
    c.saveState(); c.setFillColor(AZUL_C); c.setStrokeColor(AZUL); lw(c, 0.2)
    p = c.beginPath(); p.moveTo(*pa[0])
    for q in pa[1:]:
        p.lineTo(*q)
    p.close(); c.drawPath(p, fill=1, stroke=1); c.restoreState()
    iso_caja(c, I, CX0, CY0, C_FONDO, CX1, CY1, 0.0, NEGRO, 0.25 if det else 0.2)
    iso_caja(c, I, 9.3, -2.5, C_FONDO - 0.3, 9.7, -2.1, C_FONDO, GRIS, 0.12)
    iso_caja(c, I, 6.4, -3.4, 0.0, 7.0, -2.8, 0.15, NEGRO, 0.15)
    w = 0.8 if det else 0.55
    poly_iso(c, I, [(9.5, -2.3, C_FONDO - 0.15), (9.5, -2.3, 0.3), (11.0, -2.3, 0.3)], w)
    poly_iso(c, I, [(12.0, LOTE[1], -0.4), (12.0, -4.2, -0.4), (9.6, -4.2, -0.4), (9.6, -3.5, -0.4),
                    (9.6, -3.5, -0.6)], w * 0.8, VERDE)
    q = I.p(12.0, LOTE[1], -0.4)
    medidor(c, q[0], q[1], VERDE, 1.6 if det else 1.1)
    for yy in (-3.0, -2.0):
        poly_iso(c, I, [(11.0, yy, 0.3), (11.8, yy, 0.3)], w)
    poly_iso(c, I, [(11.0, -3.0, 0.3), (11.0, -2.0, 0.3)], w)
    poly_iso(c, I, [(11.8, -3.0, 0.3), (11.8, -1.6, 0.3)], w)
    poly_iso(c, I, [(11.8, -1.6, 0.3), (12.5, -1.6, 0.3)], w * 0.8)
    for yy, nb in ((-3.0, 'B-1'), (-2.0, 'B-2')):
        q = I.p(11.4, yy, 0.3)
        r = 2.8 if det else 1.4
        c.saveState(); c.setFillColor(colors.white); c.setStrokeColor(AZUL); lw(c, 0.3)
        c.circle(q[0], q[1], r, fill=1); c.restoreState()
        texto(c, q[0], q[1] - 0.6, nb, 1.9 if det else 1.1, 'Helvetica-Bold', 'c', AZUL)
    q = I.p(12.5, -1.6, 0.3)
    hT, wT = (11.0, 5.0) if det else (4.5, 2.2)
    c.saveState(); c.setFillColor(colors.white); c.setStrokeColor(AZUL); lw(c, 0.3)
    c.roundRect(q[0] - wT / 2, q[1], wT, hT, wT / 2 - 0.1, fill=1); c.restoreState()
    texto(c, q[0], q[1] + hT / 2 - 0.6, 'T', 1.9 if det else 1.2, 'Helvetica-Bold', 'c', AZUL)
    iso_caja(c, I, MAQ[0], MAQ[1], 0.0, MAQ[2], MAQ[3], 2.2, GRIS, 0.12, (1.5, 1))
    if not det:
        q = I.p(CX1, CY0, C_FONDO)
        texto(c, q[0] + 3, q[1] - 1, 'Cisterna y equipo:', 1.8, 'Helvetica-Bold')
        texto(c, q[0] + 3, q[1] - 3.6, 'ver detalle (derecha)', 1.8)
        return
    poly_iso(c, I, [(11.8, -1.6, 0.3), (11.8, -0.3, 0.3), (11.8, -0.3, -0.3), (9.0, -0.3, -0.3)], 0.8)
    poly_iso(c, I, [(9.0, -0.3, -0.3), (8.0, -0.3, -0.3)], 0.8, AZUL, (3, 1.2))
    for yy in (-3.0, -2.0):
        q = I.p(11.65, yy, 0.3)
        valvula(c, q[0], q[1], ang_iso(I, (11.0, yy, 0.3), (11.8, yy, 0.3)), AZUL, 1.0)
    q = I.p(11.8, -1.0, 0.3)
    valvula(c, q[0], q[1], ang_iso(I, (11.8, -1.6, 0.3), (11.8, -0.3, 0.3)), AZUL, 1.0)
    q = I.p(9.6, -3.5, -0.6)
    valvula(c, q[0], q[1] - 0.5, 90, VERDE, 0.9)

    def rot(x, y, z, s, dx, dy, al='l', col=NEGRO, b=False):
        q = I.p(x, y, z)
        c.saveState(); lw(c, 0.1); c.setStrokeColor(GRIS); c.line(q[0], q[1], q[0] + dx, q[1] + dy)
        c.restoreState()
        texto(c, q[0] + dx + (0.8 if al == 'l' else -0.8), q[1] + dy - 0.6, s, t,
              'Helvetica-Bold' if b else 'Helvetica', al, col)
    rot(12.5, -1.6, 1.0, 'T: tanque hidroneumático precargado', 16, 10)
    rot(11.4, -2.0, 0.3, 'B-2: bomba de reserva (alterna)', 26, 6)
    rot(11.4, -3.0, 0.3, 'B-1: bomba centrífuga', 26, -6)
    rot(11.8, -1.0, 0.3, 'Válvulas check y de compuerta', 18, -16)
    rot(MAQ[0], MAQ[1], 2.2, 'Cuarto de máquinas', 6, 12, b=True)
    rot(8.5, -0.3, -0.3, 'Línea enterrada Ø50 a montantes 1 y 2', -10, 22, 'r', AZUL, True)
    rot(12.0, LOTE[1], -0.4, 'Toma municipal Ø25 con medidor', 4, -14, 'l', VERDE, True)
    rot(9.6, -3.5, -0.6, 'Válvula de flotador', -12, -24, 'r', VERDE)
    rot(9.5, -2.3, C_FONDO - 0.15, 'Pichancha / válvula de pie', 6, -16, 'l', AZUL)
    rot(9.5, -2.3, -1.0, 'Succión Ø50', 10, -3, 'l', AZUL, True)
    rot(9.5, -2.3, C_FONDO - 0.3, 'Cárcamo de succión', -14, -14, 'r')
    rot(6.7, -3.1, 0.15, 'Registro hermético 0.60 x 0.60', -2, 26, 'r')
    poly_iso(c, I, [(6.8, -1.2, 0.0), (6.8, -1.2, 1.0)], 0.4, GRIS)
    rot(6.8, -1.2, 1.0, 'Tubo de ventilación con malla', -4, 6, 'r')
    for zz in (C_AGUA - 0.1, C_FONDO + 0.2):
        poly_iso(c, I, [(8.0, -1.4, 0.0), (8.0, -1.4, zz)], 0.12, GRIS)
        q = I.p(8.0, -1.4, zz)
        c.saveState(); lw(c, 0.2); c.circle(q[0], q[1], 0.9); c.restoreState()
    rot(8.0, -1.4, C_FONDO + 0.2, 'Electronivel: paro por bajo nivel', -22, -2, 'r')
    rot(8.0, -1.4, C_AGUA - 0.1, 'Electronivel: nivel alto', -22, 4, 'r')
    rot(CX0, CY1, C_AGUA, 'N.A.M. %.2f' % C_AGUA, -8, 0, 'r', AZUL)
    rot(CX0, CY1, C_FONDO, 'Fondo %.2f' % C_FONDO, -8, 0, 'r')
    rot(CX0, CY1, 0.0, '±0.00 N.T.N.', -8, 0, 'r')


def lamina_IH02(c):
    marco(c, 'IH-02', ['Isométrico general', 'de agua potable', 'Cisterna · equipo · montantes'], 'Sin escala', 4)
    I = Iso(150, 58, 5.0, 13.5)
    for lev in range(4):
        iso_linea(c, I, [(0, 0, 0, lev), (BX, 0, 0, lev), (BX, BY, 0, lev), (0, BY, 0, lev), (0, 0, 0, lev)],
                  0.12, GRIS_C, (2, 1.5))
    iso_cisterna(c, I, False)
    # línea principal y montantes
    poly_iso(c, I, [(11.8, -1.6, 0.3), (11.8, -0.3, 0.3), (11.8, -0.3, -0.3), (8.0, -0.3, -0.3),
                    (8.0, RIS_R[1], -0.3)], 0.7, AZUL, (3, 1.2))
    for (rx, ry), nom in ((RIS_F, 'M-1'), (RIS_R, 'M-2')):
        pts = [(rx, ry, -0.3, 0)] + [(rx, ry, ZP, lev) for lev in range(4)] + [(rx, ry, 3.3, 3)]
        poly_iso(c, I, pts, 0.75)
        for lev in range(4):
            a = (rx, ry, ZP, lev - 1) if lev else (rx, ry, -0.3, 0)
            rot_iso(c, I, a, (rx, ry, ZP, lev), DIAM_MONT[lev], 1.5)
        q = I.p(rx, ry, 3.3, 3)
        c.saveState(); c.setFillColor(colors.white); c.setStrokeColor(AZUL); lw(c, 0.3)
        c.rect(q[0] - 0.8, q[1], 1.6, 1.8, fill=1); c.restoreState()
        texto(c, q[0], q[1] + 2.6, nom, 1.9, 'Helvetica-Bold', 'c', AZUL)
    q = I.p(8.0, RIS_F[1], -0.3, 0)
    rot_iso(c, I, (11.8, -0.3, -0.3), (8.0, -0.3, -0.3), 'Ø50', 1.5)
    for lev in range(4):
        for apt in APTS:
            red_depto_iso(c, I, apt, lev, rot=False)
    # rótulos de deptos en el nivel 3
    for apt in APTS:
        X, Y = M(apt, 3.0, 7.2)
        q = I.p(X, Y, ZP, 3)
        texto(c, q[0], q[1] + 1.2, depto_nombre(3, apt), 1.7, 'Helvetica-Bold', 'c')
    for lev in range(4):
        q = I.p(RIS_F[0], RIS_F[1], ZP, lev)
        x0 = 24
        c.saveState(); lw(c, 0.12); c.setStrokeColor(GRIS); c.setDash([1, 1], 0)
        c.line(x0 + 42, q[1], x0 + 62, q[1]); c.restoreState()
        texto(c, x0, q[1] + 2.0, '%s  N.P.T. %s' % (NIVELES[lev], NPT[lev]), 2.5, 'Helvetica-Bold')
        texto(c, x0, q[1] - 1.4, 'Deptos. %s a %s' % (depto_nombre(lev, 'A'), depto_nombre(lev, 'D')), 2.0)
    texto(c, 24, 388, 'ISOMÉTRICO GENERAL DE AGUA POTABLE', 4.2, 'Helvetica-Bold')
    texto(c, 24, 382, 'Sin escala · entrepiso ampliado para claridad · 2 montantes (M-1: deptos. A y B; '
          'M-2: deptos. C y D) · red de cada depto. igual al isométrico tipo (IH-03)', 2.0)
    leyenda(c, 380, 392)
    D = Iso(150, 132, 20, 0)
    iso_cisterna(c, D, True)
    titulo_dibujo(c, 300, 322, 'DETALLE ISOMÉTRICO: CISTERNA Y EQUIPO', 'Sin escala')
    parrafo(c, 300, 60, [
        '**CISTERNA',
        'Interior 4.00 x 3.00 m · tirante útil 2.40 m',
        'Concreto impermeable, tapa 0.15 sobre N.T.N.',
        'Registro hermético y tubo de ventilación',
    ], 2.0)
    parrafo(c, 385, 60, [
        '**EQUIPO DE BOMBEO',
        '2 bombas alternadas + tanque hidroneumático',
        'Paro automático por bajo nivel en cisterna',
        'Sin tinacos: suministro presurizado',
    ], 2.0)


def lamina_IH03(c):
    marco(c, 'IH-03', ['Isométrico departamento tipo', '(agua fría y caliente)', 'Detalles de cisterna'],
          'Sin escala / 1:40', 5)
    I = Iso(170, 108, 21, 0)
    # muros del depto A a nivel de piso
    for (o, k, a, b, t, vanos) in MUROS_A + [('h', 0, 0, 8, 0, []), ('h', 7.5, 0, 8, 0, []),
                                              ('v', 0, 0, 7.5, 0, []), ('v', 8, 0, 7.5, 0, [])]:
        if o == 'h':
            iso_linea(c, I, [(a, k, 0), (b, k, 0)], 0.12, GRIS_C)
        else:
            iso_linea(c, I, [(k, a, 0), (k, b, 0)], 0.12, GRIS_C)
    for (nom, x0, y0, x1, y1, tp) in CUARTOS_A:
        q = I.p(tp[0], tp[1], 0)
        texto(c, q[0], q[1], nom, 2.0, al='c', col=GRIS)
    rx, ry = RIS_F
    poly_iso(c, I, [(rx, ry, -0.8, 0), (rx, ry, 3.4, 0)], 1.0)
    q = I.p(rx, ry, 3.4, 0)
    texto(c, q[0] + 1.5, q[1] + 0.8, 'Montante 1 (Ø según nivel)', 2.0, 'Helvetica-Bold', col=AZUL)
    red_depto_iso(c, I, 'A', 0, rot=True, t=2.0, ac=True)
    for (a, b, s) in (((4.65, 6.15), (1.5, 6.15), 'AC Ø13'), ((4.65, 6.15), (6.1, 6.15), 'AC Ø13')):
        rot_iso(c, I, (*a, ZPC), (*b, ZPC), s, 1.8, ROJO, abajo=True)
    for (x, y, z, s) in AF_BAJADAS:
        q = I.p(x, y, z)
        texto(c, q[0] + 1.0, q[1] + 0.4, '+%.2f' % z, 1.6, col=GRIS)
    q = I.p(4.65, 6.3, 1.5)
    c.saveState(); c.setFillColor(colors.white); c.setStrokeColor(NEGRO); lw(c, 0.3)
    c.roundRect(q[0] - 1.6, q[1] - 1.0, 3.2, 4.2, 0.6, fill=1); c.restoreState()
    c.saveState(); lw(c, 0.1); c.setStrokeColor(GRIS); c.line(q[0] - 1.6, q[1] + 2, q[0] - 12, q[1] + 12)
    c.restoreState()
    texto(c, q[0] - 12.5, q[1] + 12.4, 'Calentador eléctrico de paso', 1.8, 'Helvetica-Bold', 'r')
    q = I.p(rx, ry, ZP)
    texto(c, q[0] + 2, q[1] - 5, 'Llave de paso + medidor', 1.8, col=AZUL)
    texto(c, 24, 388, 'ISOMÉTRICO DEPARTAMENTO TIPO  (los 16 deptos. son iguales o simétricos)', 4.0,
          'Helvetica-Bold')
    texto(c, 24, 382, 'Sin escala · AF azul continuo · AC rojo discontinuo · diámetros en mm · '
          'salidas en m sobre N.P.T.', 2.2)
    parrafo(c, 24, 372, [
        '**Muebles por departamento',
        'Baño completo: W.C., lavabo y regadera',
        'Cocina: fregadero · Lavado: lavadora',
        'Calentador eléctrico de paso',
        '',
        '**Diámetros',
        '13 = 1/2"   19 = 3/4"   25 = 1"',
    ], 2.1)

    # ---------------- detalle cisterna: planta ----------------
    k = 1000 / 40.0
    vv = Vista(352 - (CX0 - 0.2) * k, 282 - (CY0 - 0.2) * k, 40)
    rect_m(c, vv, CX0 - 0.2, CY0 - 0.2, CX1 + 0.2, CY1 + 0.2, fill=GRIS_C, stroke=NEGRO, w=0.3)
    rect_m(c, vv, CX0, CY0, CX1, CY1, fill=AZUL_C, stroke=NEGRO, w=0.2)
    rect_m(c, vv, 6.4, -3.4, 7.0, -2.8, fill=colors.white, stroke=NEGRO, w=0.25)
    px, py = vv.p(6.7, -3.15); texto(c, px, py, 'Registro', 1.5, al='c')
    rect_m(c, vv, 9.3, -2.5, 9.7, -2.1, fill=colors.white, stroke=NEGRO, w=0.2, dash=(1.5, 1))
    px, py = vv.p(9.5, -1.95); texto(c, px, py, 'Cárcamo', 1.5, al='c')
    px, py = vv.p(9.5, -2.3)
    c.saveState(); c.setFillColor(AZUL); c.circle(px, py, 0.9, fill=1, stroke=0); c.restoreState()
    linea_m(c, vv, [(9.5, -2.3), (10.2, -2.3)], 0.6, AZUL)
    linea_m(c, vv, [(10.2, -3.5), (9.6, -3.5)], 0.5, VERDE)
    px, py = vv.p(10.25, -3.6); texto(c, px, py, 'Llenado', 1.5, col=VERDE)
    px, py = vv.p(10.25, -2.4); texto(c, px, py, 'Succión', 1.5, col=AZUL)
    for (x, y, s) in ((8.0, -1.4, 'Electroniveles'), (6.8, -1.2, 'Ventila')):
        px, py = vv.p(x, y)
        c.saveState(); lw(c, 0.2); c.circle(px, py, 0.8); c.restoreState()
        texto(c, px, py + 1.3, s, 1.4, al='c')
    cota_h(c, vv, CX0, CX1, CY0 - 0.2, -5)
    cota_h(c, vv, CX0 - 0.2, CX1 + 0.2, CY0 - 0.2, -10)
    cota_v(c, vv, CY0, CY1, CX1 + 0.2, 6)
    cota_v(c, vv, CY0 - 0.2, CY1 + 0.2, CX1 + 0.2, 11)
    linea_m(c, vv, [(CX0 - 0.5, -2.3), (CX1 + 0.5, -2.3)], 0.2, NEGRO, (5, 1, 1, 1))
    px, py = vv.p(CX0 - 0.55, -2.25); texto(c, px, py, 'B', 2.6, 'Helvetica-Bold', 'r')
    px, py = vv.p(CX1 + 0.55, -2.25); texto(c, px + 9, py, "B'", 2.6, 'Helvetica-Bold')
    titulo_dibujo(c, 345, 262, 'DETALLE CISTERNA · PLANTA', 'Esc. 1:40')

    # ---------------- detalle cisterna: corte B-B' ----------------
    vv = Vista(362 - (CX0 - 0.2) * k, 140 - (C_FONDO - 0.2) * k, 40)
    rect_m(c, vv, CX0 - 0.2, C_FONDO - 0.2, CX1 + 0.2, 0.15, fill=GRIS_C, stroke=NEGRO, w=0.3)
    rect_m(c, vv, CX0, C_FONDO, CX1, 0.0, fill=colors.white, stroke=NEGRO, w=0.2)
    rect_m(c, vv, CX0, C_FONDO, CX1, C_AGUA, fill=AZUL_C, stroke=None)
    linea_m(c, vv, [(CX0, C_AGUA), (CX1, C_AGUA)], 0.25, AZUL)
    rect_m(c, vv, 9.3, C_FONDO - 0.3, 9.7, C_FONDO, fill=AZUL_C, stroke=NEGRO, w=0.2)
    rect_m(c, vv, 6.4, 0.0, 7.0, 0.15, fill=colors.white, stroke=NEGRO, w=0.15)
    rect_m(c, vv, 6.35, 0.15, 7.05, 0.2, fill=NEGRO, stroke=None)
    linea_m(c, vv, [(9.5, C_FONDO - 0.15), (9.5, 0.45), (10.4, 0.45)], 0.7, AZUL)
    px, py = vv.p(9.4, -1.3); texto(c, px, py, 'Succión Ø50', 1.6, 'Helvetica-Bold', 'r', AZUL)
    linea_m(c, vv, [(10.4, -0.25), (8.9, -0.25), (8.9, -0.45)], 0.5, VERDE)
    px, py = vv.p(8.6, -0.55)
    c.saveState(); lw(c, 0.2); c.setStrokeColor(VERDE); c.circle(px, py, 1.3); c.restoreState()
    px, py = vv.p(8.3, -0.15); texto(c, px, py, 'Válv. de flotador', 1.5, al='r', col=VERDE)
    linea_m(c, vv, [(8.0, 0.0), (8.0, C_FONDO + 0.2)], 0.15, GRIS)
    for zz in (C_AGUA - 0.1, C_FONDO + 0.2):
        px, py = vv.p(8.0, zz)
        c.saveState(); lw(c, 0.2); c.circle(px, py, 0.8); c.restoreState()
    px, py = vv.p(7.9, C_FONDO + 0.15); texto(c, px, py, 'Paro bajo nivel', 1.5, al='r')
    linea_m(c, vv, [(6.8, 0.15), (6.8, 0.8), (7.0, 0.8)], 0.3, GRIS)
    cota_v(c, vv, C_FONDO, C_AGUA, CX1 + 0.2, 6, '2.40 útil')
    cota_v(c, vv, C_AGUA, 0.0, CX1 + 0.2, 6, '0.40')
    cota_v(c, vv, C_FONDO, 0.0, CX1 + 0.2, 12)
    cota_h(c, vv, CX0, CX1, C_FONDO - 0.2, -5)
    for z, s in ((0.15, '+0.15 Tapa'), (0.0, '±0.00 N.T.N.'), (C_AGUA, '%.2f N.A.M.' % C_AGUA),
                 (C_FONDO, '%.2f Fondo' % C_FONDO)):
        px, py = vv.p(CX0 - 0.25, z)
        nivel_marca(c, px - 1, py, s, 1.5, izq=True)
    titulo_dibujo(c, 345, 120, "DETALLE CISTERNA · CORTE B-B'", 'Esc. 1:40')
    parrafo(c, 345, 108, [
        'Muros y losa de concreto con impermeabilizante integral;',
        'aplanado pulido interior; chaflanes en esquinas;',
        'fondo con pendiente hacia el cárcamo de succión;',
        'tapa 15 cm sobre N.T.N. para evitar escurrimientos;',
        'a más de 3 m de albañales y registros sanitarios.',
    ], 1.9)


def main():
    c = canvas.Canvas(SALIDA, pagesize=(PW * mm, PH * mm))
    c.setTitle('Edificio 4 niveles, 16 departamentos - Planos e isométrico de agua potable')
    for f in (lamina_A01, lamina_A02, lamina_IH01, lamina_IH02, lamina_IH03):
        c.saveState(); c.scale(mm, mm)
        f(c)
        c.restoreState(); c.showPage()
    c.save()
    print('PDF:', SALIDA)
    # DXF: mismas láminas, una junto a otra en el espacio modelo (mm de pliego)
    from dxf_canvas import DXFCanvas
    d = DXFCanvas()
    for i, f in enumerate((lamina_A01, lamina_A02, lamina_IH01, lamina_IH02, lamina_IH03)):
        d.saveState(); d.translate(i * (PW + 50), 0)
        f(d)
        d.restoreState()
    d.save(SALIDA_DXF)
    print('DXF:', SALIDA_DXF)


if __name__ == '__main__':
    main()
