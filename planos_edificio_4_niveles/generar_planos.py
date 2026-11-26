# -*- coding: utf-8 -*-
"""
Genera el juego de planos (PDF, A2 horizontal) de un edificio habitacional
de 4 niveles, 1 departamento por nivel (3 recámaras, 2½ baños), con
instalación hidráulica de agua potable: cisterna, equipo de bombeo a
presión constante, montante, isométricos y memoria de cálculo.

Todo el cálculo hidráulico (unidades mueble, gastos, diámetros,
velocidades, pérdidas y presiones) se hace aquí mismo y se imprime en
la memoria, de modo que el plano y la memoria siempre coinciden.

Uso:  python3 generar_planos.py
"""
import math
import os
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "Planos_Edificio_4_niveles_Agua_Potable.pdf")

PW, PH = 594.0, 420.0          # A2 horizontal, en mm
NEGRO = colors.black
GRIS = colors.Color(.45, .45, .45)
GRIS_C = colors.Color(.72, .72, .72)
GRIS_MC = colors.Color(.88, .88, .88)
AZUL = colors.Color(0.0, 0.33, 0.80)
AZUL_C = colors.Color(.80, .90, 1.0)
ROJO = colors.Color(.85, .10, .10)
VERDE = colors.Color(0.0, 0.50, 0.20)

FECHA = "Noviembre 2026"
H_NIVEL = 3.00                 # altura de entrepiso (m)
NIVELES = ["Planta Baja", "Nivel 1", "Nivel 2", "Nivel 3"]
DEPTOS = ["Depto. 101", "Depto. 201", "Depto. 301", "Depto. 401"]
Z_PLAFON = 2.60                # tubería de AF por plafón (sobre NPT)
Z_PLAFON_AC = 2.50             # tubería de AC por plafón

# ----------------------------------------------------------------------
#  DATOS DE CÁLCULO
# ----------------------------------------------------------------------
# Tubería de cobre tipo M: nominal (mm), pulgadas, diámetro interior (m)
TUBOS = [(13, '1/2"', 0.01445), (19, '3/4"', 0.02061), (25, '1"', 0.02680),
         (32, '1 1/4"', 0.03280), (38, '1 1/2"', 0.03880), (50, '2"', 0.05100),
         (64, '2 1/2"', 0.06310)]
V_MAX = 2.0                    # m/s
C_HW = 130                     # Hazen-Williams, cobre
F_ACCES = 1.25                 # longitud equivalente por accesorios (+25 %)
P_CONSIGNA = 32.0              # m.c.a. en la descarga del equipo (3.2 kg/cm²)
P_MIN = 10.0                   # m.c.a. mínima en la salida más desfavorable
P_MAX = 40.0                   # m.c.a. máxima estática admisible en muebles
H_MEDIDOR = 1.5                # pérdida en válvula + medidor por depto (m)

# Muebles: UM (Hunter, uso privado, tanque), gasto individual (L/s),
# altura de la salida (m), nombre.
MUEBLES = {
    'WC':  (3, 0.10, 0.25, 'W.C. de tanque'),
    'LAV': (1, 0.10, 0.55, 'Lavabo'),
    'REG': (2, 0.20, 1.10, 'Regadera (mezcladora)'),
    'FRE': (2, 0.20, 0.55, 'Fregadero'),
    'LDR': (3, 0.20, 1.00, 'Lavadero'),
    'LVD': (2, 0.20, 1.00, 'Lavadora'),
    'CAL': (0, 0.27, 1.50, 'Calentador de paso 16 L/min'),
}
ABREV = {'WC': 'W.C.', 'LAV': 'Lav.', 'REG': 'Reg.', 'FRE': 'Freg.',
         'LDR': 'Ldro.', 'LVD': 'Lavad.', 'CAL': 'Cal.'}

# Curva de Hunter (sistemas con W.C. de tanque), UM -> gpm (IPC, apéndice E)
HUNTER = [(0, 0), (1, 3.0), (2, 5.0), (3, 6.5), (4, 8.0), (5, 9.4), (6, 10.7),
          (7, 11.8), (8, 12.8), (9, 13.7), (10, 14.6), (11, 15.4), (12, 16.0),
          (13, 16.5), (14, 17.0), (15, 17.5), (16, 18.0), (17, 18.4),
          (18, 18.8), (19, 19.2), (20, 19.6), (25, 21.5), (30, 23.3),
          (35, 24.9), (40, 26.3), (45, 27.7), (50, 29.1), (60, 32.0),
          (70, 35.0), (80, 38.0), (90, 41.0), (100, 43.5), (120, 48.0)]


def hunter_lps(um):
    for (a, qa), (b, qb) in zip(HUNTER, HUNTER[1:]):
        if a <= um <= b:
            return (qa + (qb - qa) * (um - a) / (b - a)) * 0.0631
    raise ValueError(um)


def hazen(q, d, L):
    if q <= 0:
        return 0.0
    return 10.67 * L * q ** 1.852 / (C_HW ** 1.852 * d ** 4.87)


# ---------------------------- Proyecto --------------------------------
OCUP_DEPTO = 7                 # 3 recámaras x 2 + 1
DOTACION = 200                 # L/hab/día
DIAS = 3                       # 1 día de consumo + 2 de reserva (sin tinacos)
CIS_X0, CIS_X1, CIS_Y0, CIS_Y1 = 5.0, 8.0, -3.3, -0.7   # interior cisterna
CIS_FONDO, CIS_AGUA = -2.60, -0.40                       # NPT fondo / nivel máx.

# ----------------------------------------------------------------------
#  RED DE AGUA FRÍA (árbol) — coordenadas en m; z local sobre el NPT
# ----------------------------------------------------------------------
RISER_XY = (5.0, 5.6)


class Red:
    def __init__(self):
        self.n = {}        # nombre -> dict(x,y,z,lev,fix)
        self.hijos = {}
        self.padre = {}
        self.info = {}     # arista (p,h) -> dict

    def nodo(self, nom, x, y, z, lev=0, fix=None):
        self.n[nom] = dict(x=x, y=y, z=z, lev=lev, fix=fix)
        self.hijos.setdefault(nom, [])

    def arista(self, p, h, **kw):
        self.hijos[p].append(h)
        self.padre[h] = p
        self.info[(p, h)] = dict(kw)

    def ztrue(self, nom):
        d = self.n[nom]
        return d['lev'] * H_NIVEL + d['z']


def arbol_depto(r, lev, raiz):
    """Agrega la red de AF de un departamento colgando del nodo raiz."""
    s = '_%d' % lev
    zp = Z_PLAFON

    def N(nom, x, y, z=zp, fix=None):
        r.nodo(nom + s, x, y, z, lev, fix)

    def E(a, b, **kw):
        r.arista(a + s if a != raiz else raiz, b + s, **kw)

    N('A', 5.0, 6.4)
    E(raiz, 'A', medidor=True)
    # rama poniente: medio baño, baño 2 y baño principal
    N('B', 4.2, 6.4); E('A', 'B')
    N('D', 4.2, 7.05); E('B', 'D')
    N('m1', 3.1, 7.05); E('D', 'm1')
    N('LAVmb', 3.1, 7.05, MUEBLES['LAV'][2], 'LAV'); E('m1', 'LAVmb')
    N('m2', 2.25, 7.05); E('m1', 'm2')
    N('WCmb', 2.25, 7.05, MUEBLES['WC'][2], 'WC'); E('m2', 'WCmb')
    N('C', 4.2, 12.2); E('D', 'C')
    N('b1', 2.7, 12.2); E('C', 'b1')
    N('LAVb2', 2.7, 12.2, MUEBLES['LAV'][2], 'LAV'); E('b1', 'LAVb2')
    N('b2', 1.75, 12.2); E('b1', 'b2')
    N('WCb2', 1.75, 12.2, MUEBLES['WC'][2], 'WC'); E('b2', 'WCb2')
    N('b3', 0.55, 12.2); E('b2', 'b3')
    N('REGb2', 0.55, 12.2, MUEBLES['REG'][2], 'REG'); E('b3', 'REGb2')
    N('E', 4.2, 13.0); E('C', 'E')
    N('p1', 6.6, 13.0); E('E', 'p1')
    N('LAVbp', 6.6, 13.0, MUEBLES['LAV'][2], 'LAV'); E('p1', 'LAVbp')
    N('p2', 7.7, 13.0); E('p1', 'p2')
    N('WCbp', 7.7, 13.0, MUEBLES['WC'][2], 'WC'); E('p2', 'WCbp')
    N('p3', 9.8, 13.0); E('p2', 'p3')
    N('p4', 9.8, 13.8); E('p3', 'p4')
    N('REGbp', 9.8, 13.8, MUEBLES['REG'][2], 'REG'); E('p4', 'REGbp')
    # rama oriente: cocina, lavandería y calentador
    N('F', 9.75, 6.4); E('A', 'F')
    N('k1', 9.75, 7.2); E('F', 'k1')
    N('FRE', 9.75, 7.2, MUEBLES['FRE'][2], 'FRE'); E('k1', 'FRE')
    N('k2', 9.75, 9.2); E('k1', 'k2')
    N('LDR', 9.75, 9.2, MUEBLES['LDR'][2], 'LDR'); E('k2', 'LDR')
    N('k3', 9.75, 10.1); E('k2', 'k3')
    N('LVD', 9.75, 10.1, MUEBLES['LVD'][2], 'LVD'); E('k3', 'LVD')
    N('k4', 9.75, 10.35); E('k3', 'k4')
    N('k5', 8.4, 10.35); E('k4', 'k5')
    N('CAL', 8.4, 10.35, MUEBLES['CAL'][2], 'CAL'); E('k5', 'CAL')


def construir_red():
    r = Red()
    rx, ry = RISER_XY
    # equipo -> línea principal enterrada -> montante
    r.nodo('EQ', 9.5, -1.2, 0.30)
    r.nodo('P1', 9.5, -0.2, 0.30); r.arista('EQ', 'P1', tipo='principal')
    r.nodo('P2', 9.5, -0.2, -0.30); r.arista('P1', 'P2', tipo='principal')
    r.nodo('P3', rx, -0.2, -0.30); r.arista('P2', 'P3', tipo='principal')
    r.nodo('P4', rx, ry, -0.30); r.arista('P3', 'P4', tipo='principal')
    prev = 'P4'
    for lev in range(4):
        nom = 'R%d' % lev
        r.nodo(nom, rx, ry, Z_PLAFON, lev)
        r.arista(prev, nom, tipo='montante')
        arbol_depto(r, lev, nom)
        prev = nom
    r.nodo('AIRE', rx, ry, 3.30, 3)
    r.arista(prev, 'AIRE', tipo='aire')
    calcular(r)
    return r


def calcular(r):
    # UM y gasto individual acumulados aguas abajo
    def acum(nom):
        d = r.n[nom]
        um, qi, nf = 0, 0.0, 0
        if d['fix']:
            m = MUEBLES[d['fix']]
            um, qi, nf = m[0], m[1], 1
        for h in r.hijos[nom]:
            a, b, c = acum(h)
            um += a; qi += b; nf += c
        d['um'], d['qi'], d['nf'] = um, qi, nf
        return um, qi, nf
    acum('EQ')
    for (p, h), inf in r.info.items():
        d = r.n[h]
        um, qi, nf = d['um'], d['qi'], d['nf']
        if nf == 0:
            inf.update(q=0, dn=TUBOS[2], v=0, L=0, hf=0, um=0)
            continue
        q = min(hunter_lps(um), qi) if um > 0 else qi
        dmin = 13 if nf == 1 else 19
        dn = None
        for t in TUBOS:
            if t[0] < dmin:
                continue
            v = q / 1000 / (math.pi * t[2] ** 2 / 4)
            if v <= V_MAX:
                dn = t
                break
        v = q / 1000 / (math.pi * dn[2] ** 2 / 4)
        P, H = r.n[p], r.n[h]
        L = math.sqrt((P['x'] - H['x']) ** 2 + (P['y'] - H['y']) ** 2 +
                      (r.ztrue(p) - r.ztrue(h)) ** 2)
        hf = hazen(q / 1000, dn[2], L * F_ACCES)
        if inf.get('medidor'):
            hf += H_MEDIDOR
        inf.update(q=q, dn=dn, v=v, L=L, hf=hf, um=um)
    # presiones
    r.n['EQ']['p'] = P_CONSIGNA

    def pres(nom):
        for h in r.hijos[nom]:
            inf = r.info[(nom, h)]
            r.n[h]['p'] = (r.n[nom]['p'] - (r.ztrue(h) - r.ztrue(nom)) -
                           inf['hf'])
            pres(h)
    pres('EQ')


RED = construir_red()

# Resultados globales
UM_DEPTO = RED.n['A_0']['um']
UM_TOTAL = RED.n['P4']['um']
Q_TOTAL = RED.info[('EQ', 'P1')]['q']
CONSUMO = OCUP_DEPTO * 4 * DOTACION
V_CIS_REQ = CONSUMO * DIAS / 1000.0
V_CIS_UTIL = (CIS_X1 - CIS_X0) * (CIS_Y1 - CIS_Y0) * (CIS_AGUA - CIS_FONDO)
Z_SUCC_MIN = CIS_FONDO + 0.20          # nivel de paro por bajo nivel
CDT = P_CONSIGNA + (0.30 - Z_SUCC_MIN) + 0.8   # + pérdidas en succión y equipo
ETA = 0.55
POT_KW = 9.81 * Q_TOTAL / 1000 * CDT / ETA
POT_HP = POT_KW / 0.746
HP_COM = next(h for h in (0.5, 0.75, 1, 1.5, 2, 3, 5, 7.5, 10) if h >= POT_HP)


def presion_salida(nom):
    """Presión en la salida (regadera: en la cebolleta, 0.80 m arriba)."""
    d = RED.n[nom]
    p = d['p']
    if d['fix'] == 'REG':
        p -= 0.80
    return p


FIXT = [k for k, d in RED.n.items() if d['fix'] and d['fix'] != 'CAL']
PEOR = min(FIXT, key=presion_salida)
P_PEOR = presion_salida(PEOR)
P_EST_MAX = max(P_CONSIGNA + 0.30 - RED.ztrue(k) for k in FIXT)

# Comparativo: tinaco por gravedad sobre azotea
Z_TINACO = 4 * H_NIVEL + 1.0 + 0.6     # base + nivel medio de agua
P_TINACO_N3 = Z_TINACO - (3 * H_NIVEL + MUEBLES['REG'][2] + 0.8) - 1.0


# ----------------------------------------------------------------------
#  UTILERÍAS DE DIBUJO
# ----------------------------------------------------------------------
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


# ----------------------------------------------------------------------
#  MARCO Y CUADRO DE DATOS
# ----------------------------------------------------------------------
TOTAL_LAMINAS = 6


def marco(c, clave, nombre, escala, num):
    lw(c, 0.7)
    c.rect(10, 10, PW - 20, PH - 20)
    lw(c, 0.2)
    c.rect(12, 12, PW - 24, PH - 24)
    x0 = PW - 107
    lw(c, 0.5)
    c.line(x0, 12, x0, PH - 12)
    xm = x0 + 4
    y = PH - 22
    texto(c, xm, y, 'PROYECTO TIPO', 4.2, 'Helvetica-Bold'); y -= 6
    texto(c, xm, y, 'Edificio habitacional de 4 niveles', 3.0, 'Helvetica-Bold'); y -= 4.4
    texto(c, xm, y, '4 departamentos (1 por nivel)', 2.5); y -= 3.6
    texto(c, xm, y, '3 recámaras · 2½ baños por departamento', 2.5); y -= 3.6
    texto(c, xm, y, 'Agua potable: cisterna + equipo de presión constante', 2.5); y -= 5
    lw(c, 0.25); c.line(x0, y, PW - 12, y); y -= 5
    texto(c, xm, y, 'DATOS DEL PROYECTO', 2.6, 'Helvetica-Bold'); y -= 4
    datos = ['Terreno: 12.00 x 23.00 m = 276.00 m²',
             'Desplante: 10.00 x 17.00 m = 170.00 m²',
             'Construida: 4 x 170.00 + caseta = 694.04 m²',
             'Altura: 12.90 m a pretil (14.70 m a caseta)',
             'Entrepiso: 3.00 m · Losas maciza 0.20 m',
             'Ocupación: %d hab/depto · %d hab totales' % (OCUP_DEPTO, OCUP_DEPTO * 4),
             'Cisterna: %.1f m³ útiles (%d días de consumo)' % (V_CIS_UTIL, DIAS),
             'Equipo: 2 bombas de %s HP + variador' % (('%g' % HP_COM)),
             ]
    y = parrafo(c, xm, y, datos, 2.15) - 2
    lw(c, 0.25); c.line(x0, y, PW - 12, y); y -= 5
    texto(c, xm, y, 'NOTAS GENERALES', 2.6, 'Helvetica-Bold'); y -= 4
    notas = ['1. Cotas y niveles en metros; rigen las cotas',
             '    sobre el dibujo a escala.',
             '2. N.P.T. = nivel de piso terminado;',
             '    N.T.N. = nivel de terreno natural (±0.00).',
             '3. Tubería de agua fría y caliente: cobre tipo M',
             '    con soldadura 50/50; en montante y',
             '    línea enterrada se admite PP-R o CPVC del',
             '    mismo diámetro interior.',
             '4. Probar la red a 10 kg/cm² durante 3 h',
             '    antes de cubrir; sin fugas ni caída.',
             '5. Desinfectar cisterna y red con cloro',
             '    (50 mg/L, 24 h) antes de su uso.',
             '6. Proyecto tipo de referencia: debe adecuarse',
             '    al reglamento local y ser avalado por el',
             '    D.R.O. / perito responsable de la obra.',
             ]
    y = parrafo(c, xm, y, notas, 2.05)
    # bloque inferior
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
    c.line(x0, 20 + 0, x0, 20)
    texto(c, xm, 15.5, 'Lámina %d de %d' % (num, TOTAL_LAMINAS), 2.4)
    texto(c, PW - 16, 15.5, clave, 7.5, 'Helvetica-Bold', 'r')


# ----------------------------------------------------------------------
#  ARQUITECTURA (planta tipo)
# ----------------------------------------------------------------------
TE, TI = 0.25, 0.15
# muros: (orientación, coord, a, b, espesor, vanos)
# vano: (a, b, tipo, bisagra, lado) tipo: P=puerta, V=ventana, H=hueco
def muros(nivel):
    pb = nivel == 0
    frente = [(0.40, 1.40, 'P', 'a', -1)] if pb else [(0.55, 2.05, 'V', None, 0)]
    return [
        ('h', 0.0, 0.0, 10.0, TE, frente + [(3.5, 9.0, 'V', None, 0)]),
        ('h', 17.0, 0.0, 10.0, TE, [(1.5, 4.0, 'V', None, 0), (7.0, 8.8, 'V', None, 0)]),
        ('v', 0.0, 0.0, 17.0, TE, [(8.2, 9.8, 'V', None, 0), (10.8, 11.3, 'V', None, 0),
                                   (14.0, 16.0, 'V', None, 0)]),
        ('v', 10.0, 0.0, 17.0, TE, []),
        ('v', 2.6, 0.0, 5.4, 0.20, [(0.45, 1.45, 'P', 'b', 1)]),
        ('h', 5.4, 0.0, 3.6, TI, []),
        ('h', 5.4, 4.8, 5.6, TI, []),
        ('v', 1.8, 5.4, 7.4, TI, []),
        ('v', 3.6, 5.4, 12.6, TI, [(5.6, 6.35, 'P', 'a', -1), (9.65, 10.45, 'P', 'b', -1),
                                   (10.75, 11.5, 'P', 'a', -1)]),
        ('h', 7.4, 0.0, 3.6, TI, [(0.15, 1.65, 'H', None, 0)]),
        ('h', 10.6, 0.0, 3.6, TI, []),
        ('h', 12.6, 0.0, 10.0, TI, [(3.75, 4.65, 'P', 'a', 1), (8.3, 9.7, 'V', None, 0)]),
        ('v', 4.8, 5.4, 12.6, TI, [(5.5, 6.1, 'H', None, 0), (9.0, 9.85, 'P', 'a', 1)]),
        ('v', 5.6, 5.4, 6.2, TI, []),
        ('h', 6.2, 4.8, 5.6, TI, []),
        ('h', 8.6, 4.8, 10.0, TI, [(8.3, 9.1, 'P', 'a', 1)]),
        ('v', 8.0, 8.6, 12.6, TI, [(10.9, 12.3, 'V', None, 0)]),
        ('h', 10.6, 8.0, 10.0, TI, [(8.25, 9.75, 'V', None, 0)]),
        ('v', 5.6, 12.6, 17.0, TI, [(12.85, 13.65, 'P', 'a', 1), (15.3, 16.1, 'P', 'a', 1)]),
        ('h', 14.6, 5.6, 10.0, TI, []),
    ]


CUARTOS = [  # nombre, x0, y0, x1, y1, (tx, ty) opcional
    ('Escalera', 0, 0, 2.6, 5.4, (1.3, 4.75)),
    ('Sala - comedor', 2.6, 0, 10, 5.4, (5.0, 2.9)),
    ('Clóset', 0, 5.4, 1.8, 7.4, (0.9, 6.3)),
    ('½ Baño', 1.8, 5.4, 3.6, 7.4, (2.7, 6.25)),
    ('Pasillo', 3.6, 5.4, 4.8, 12.6, (4.2, 9.0)),
    ('Cocina', 4.8, 5.4, 10, 8.6, (7.3, 7.6)),
    ('Recámara 2', 0, 7.4, 3.6, 10.6, (1.8, 8.6)),
    ('Baño 2', 0, 10.6, 3.6, 12.6, (2.1, 11.35)),
    ('Recámara 3', 4.8, 8.6, 8.0, 12.6, (6.4, 11.0)),
    ('Lavandería', 8.0, 8.6, 10, 10.6, (8.6, 9.65)),
    ('Cubo de luz', 8.0, 10.6, 10, 12.6, (9.0, 11.25)),
    ('Recámara principal', 0, 12.6, 5.6, 17, (2.8, 15.6)),
    ('Baño principal', 5.6, 12.6, 10, 14.6, (7.0, 14.1)),
    ('Vestidor', 5.6, 14.6, 10, 17, (7.8, 16.2)),
]


def dibujar_muros(c, v, nivel, col=NEGRO, puertas=True):
    for o, k, a, b, t, vanos in muros(nivel):
        ext = t / 2
        cortes = sorted(vanos)
        tramos, ini = [], a - ext
        for (va, vb, tipo, bis, lado) in cortes:
            tramos.append((ini, va))
            ini = vb
        tramos.append((ini, b + ext))
        for (u0, u1) in tramos:
            if u1 - u0 <= 1e-6:
                continue
            if o == 'h':
                rect_m(c, v, u0, k - t / 2, u1, k + t / 2, fill=col, stroke=None)
            else:
                rect_m(c, v, k - t / 2, u0, k + t / 2, u1, fill=col, stroke=None)
        for (va, vb, tipo, bis, lado) in cortes:
            if tipo == 'V':
                if o == 'h':
                    rect_m(c, v, va, k - t / 2, vb, k + t / 2, stroke=col, w=0.12)
                    linea_m(c, v, [(va, k - 0.02), (vb, k - 0.02)], 0.12, col)
                    linea_m(c, v, [(va, k + 0.03), (vb, k + 0.03)], 0.12, col)
                else:
                    rect_m(c, v, k - t / 2, va, k + t / 2, vb, stroke=col, w=0.12)
                    linea_m(c, v, [(k - 0.02, va), (k - 0.02, vb)], 0.12, col)
                    linea_m(c, v, [(k + 0.03, va), (k + 0.03, vb)], 0.12, col)
            elif tipo == 'P' and puertas:
                w = vb - va
                hx = va if bis == 'a' else vb
                if o == 'h':
                    cx, cy = v.p(hx, k)
                    hoja = v.p(hx, k + lado * w)
                    c.saveState(); lw(c, 0.25); c.setStrokeColor(col)
                    c.line(cx, cy, hoja[0], hoja[1])
                    lw(c, 0.1)
                    R = w * v.k
                    ang0 = 90 if lado > 0 else 270
                    ext_ang = -90 if (bis == 'a') == (lado > 0) else 90
                    if bis == 'a' and lado > 0:
                        st, ex = 0, 90
                    elif bis == 'a' and lado < 0:
                        st, ex = 270, 90
                    elif bis == 'b' and lado > 0:
                        st, ex = 90, 90
                    else:
                        st, ex = 180, 90
                    c.arc(cx - R, cy - R, cx + R, cy + R, st, ex)
                    c.restoreState()
                else:
                    cx, cy = v.p(k, hx)
                    hoja = v.p(k + lado * w, hx)
                    c.saveState(); lw(c, 0.25); c.setStrokeColor(col)
                    c.line(cx, cy, hoja[0], hoja[1])
                    lw(c, 0.1)
                    R = w * v.k
                    if bis == 'a' and lado > 0:
                        st, ex = 0, 90
                    elif bis == 'a' and lado < 0:
                        st, ex = 90, 90
                    elif bis == 'b' and lado > 0:
                        st, ex = 270, 90
                    else:
                        st, ex = 180, 90
                    c.arc(cx - R, cy - R, cx + R, cy + R, st, ex)
                    c.restoreState()


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


def escalera(c, v, col=NEGRO, nivel=0, azotea=False):
    # tramo 1: x 0.13-1.25, sube +y de 1.90 a 4.14 (8 huellas)
    # tramo 2: x 1.35-2.475, sube -y de 4.14 a 2.18 (7 huellas)
    hu = 0.28
    for i in range(9):
        y = 1.90 + i * hu
        linea_m(c, v, [(0.125, y), (1.25, y)], 0.1, col)
    for i in range(8):
        y = 4.14 - i * hu
        linea_m(c, v, [(1.35, y), (2.475, y)], 0.1, col)
    rect_m(c, v, 1.25, 1.90, 1.35, 4.14, stroke=col, w=0.12)   # alma
    # flecha
    linea_m(c, v, [(0.69, 2.0), (0.69, 4.5), (1.9, 4.5), (1.9, 2.3)], 0.12, col)
    a = v.p(1.9, 2.3)
    c.saveState(); c.setFillColor(col)
    p = c.beginPath(); p.moveTo(a[0], a[1]); p.lineTo(a[0] - 0.7, a[1] + 1.6)
    p.lineTo(a[0] + 0.7, a[1] + 1.6); p.close(); c.drawPath(p, fill=1, stroke=0)
    c.restoreState()
    tx, ty = v.p(0.69, 1.55)
    texto(c, tx, ty, 'SUBE', 1.6, al='c', col=col)
    # línea de corte
    linea_m(c, v, [(0.125, 3.2), (1.25, 3.6)], 0.12, col)


def planta_arq(c, v, nivel, modo='arq'):
    col = NEGRO if modo == 'arq' else GRIS_C
    colm = NEGRO if modo == 'arq' else GRIS
    # terreno
    if nivel == 0 and modo == 'arq' or (nivel == 0 and modo == 'hid'):
        rect_m(c, v, -2.0, -4.0, 10.0, 19.0, stroke=GRIS, w=0.2, dash=(4, 1, 1, 1))
    # cubo de luz (achurado)
    for i in range(9):
        d = i * 0.45
        x0, y0 = 8.0 + max(0, d - 2.0), 10.6 + min(d, 2.0)
        x1, y1 = 8.0 + min(d, 2.0), 10.6 + max(0, d - 2.0)
        linea_m(c, v, [(x0, y0), (x1, y1)], 0.06, GRIS_C)
    dibujar_muros(c, v, nivel, col)
    escalera(c, v, colm, nivel)
    # sanitarios
    mueble(c, v, 'WC', 2.25, 7.4, 180, colm)
    mueble(c, v, 'LAV', 3.1, 7.4, 180, colm)
    mueble(c, v, 'LAV', 2.7, 12.6, 180, colm)
    mueble(c, v, 'WC', 1.75, 12.6, 180, colm)
    regadera(c, v, 0.0, 11.45, 1.1, 12.6, colm)
    mueble(c, v, 'LAV', 6.6, 12.6, 0, colm)
    mueble(c, v, 'WC', 7.7, 12.6, 0, colm)
    regadera(c, v, 8.8, 13.0, 10.0, 14.6, colm)
    # cocina
    rect_m(c, v, 9.4, 5.4, 10.0, 8.6, stroke=colm, w=0.12)
    mueble(c, v, 'FRE', 10.0, 7.2, 90, colm)
    mueble(c, v, 'EST', 10.0, 6.05, 90, colm)
    rect_m(c, v, 5.9, 6.6, 7.9, 7.4, stroke=colm, w=0.12)   # isla
    # lavandería
    mueble(c, v, 'LDR', 10.0, 9.2, 90, colm)
    mueble(c, v, 'LVD', 10.0, 10.05, 90, colm)
    mueble(c, v, 'CAL', 8.4, 10.6, 180, colm)
    if modo == 'arq':
        mueble(c, v, 'CAMA', 2.6, 17.0, 180)
        mueble(c, v, 'CAMA1', 1.6, 7.6 + 0.0, 0)
        mueble(c, v, 'CAMA1', 8.0, 11.0, 90)
        mueble(c, v, 'SOFA', 7.0, 0.15, 0)
        mueble(c, v, 'MESA', 4.3, 1.5, 90)
        closet(c, v, 0.15, 5.5, 1.7, 7.3)
        closet(c, v, 4.9, 12.0, 6.7, 12.5)
        closet(c, v, 5.7, 16.3, 9.9, 16.9)
        closet(c, v, 3.0, 7.5, 3.5, 9.4)
    # textos de locales
    if modo == 'arq':
        for (nom, x0, y0, x1, y1, tp) in CUARTOS:
            px, py = v.p(*tp)
            texto(c, px, py, nom, 2.0, 'Helvetica-Bold', 'c')
            if nom not in ('Cubo de luz', 'Pasillo', 'Escalera', 'Clóset'):
                a = (x1 - x0) * (y1 - y0)
                if nom == 'Cocina':
                    a -= 0.8 * 0.8
                texto(c, px, py - 2.6, '%.2f m²' % a, 1.7, al='c')
    else:
        for (nom, x0, y0, x1, y1, tp) in CUARTOS:
            px, py = v.p(*tp)
            texto(c, px, py, nom, 1.8, al='c', col=GRIS)
    # ducto
    rect_m(c, v, 4.875, 5.475, 5.525, 6.125, stroke=colm, w=0.08)
    px, py = v.p(5.2, 6.35)
    texto(c, px, py, 'Ducto', 1.4, al='c', col=colm)
    # nivel de piso
    px, py = v.p(6.2, 4.1)
    npt = ['±0.00', '+3.00', '+6.00', '+9.00'][nivel] if isinstance(nivel, int) else ''
    texto(c, px, py, 'N.P.T. ' + (npt if nivel == 0 else '+3.00 / +6.00 / +9.00'),
          1.7, al='c', col=colm)


def exterior_pb(c, v, modo='arq'):
    col = NEGRO if modo == 'arq' else GRIS
    # banqueta / alineamiento
    linea_m(c, v, [(-2.0, -4.0), (10.0, -4.0)], 0.35, col)
    px, py = v.p(4.0, -5.3)
    texto(c, px, py, 'ALINEAMIENTO  —  CALLE', 2.0, 'Helvetica-Bold', 'c', col)
    # cisterna (muros 0.20)
    rect_m(c, v, CIS_X0 - 0.2, CIS_Y0 - 0.2, CIS_X1 + 0.2, CIS_Y1 + 0.2,
           fill=GRIS_MC if modo == 'arq' else AZUL_C, stroke=col, w=0.25)
    rect_m(c, v, CIS_X0, CIS_Y0, CIS_X1, CIS_Y1, fill=colors.white, stroke=col, w=0.15)
    rect_m(c, v, 5.3, -2.9, 5.9, -2.3, stroke=col, w=0.15)          # registro
    linea_m(c, v, [(5.3, -2.9), (5.9, -2.3)], 0.08, col)
    linea_m(c, v, [(5.3, -2.3), (5.9, -2.9)], 0.08, col)
    rect_m(c, v, 7.4, -2.2, 7.8, -1.8, stroke=col, w=0.1, dash=(1, 0.8))  # cárcamo
    px, py = v.p(6.5, -1.45)
    texto(c, px, py, 'CISTERNA', 2.0, 'Helvetica-Bold', 'c', col)
    texto(c, px, py - 2.5, '%.1f m³' % V_CIS_UTIL, 1.7, al='c', col=col)
    # cuarto de máquinas
    rect_m(c, v, 8.4, -3.5, 10.0, -0.5, stroke=col, w=0.25)
    rect_m(c, v, 8.5, -3.4, 9.9, -0.6, stroke=col, w=0.1)
    px, py = v.p(9.2, -3.1)
    texto(c, px, py, 'C. MÁQ.', 1.6, 'Helvetica-Bold', 'c', col)
    # andador lateral y acceso
    px, py = v.p(-1.0, 8.5)
    texto(c, px, py, 'ANDADOR / JARDÍN LATERAL', 1.8, al='c', col=col, rot=90)
    px, py = v.p(2.2, -2.2)
    texto(c, px, py, 'ACCESO', 2.0, 'Helvetica-Bold', 'c', col)
    linea_m(c, v, [(0.9, -3.8), (0.9, -0.3)], 0.15, col)
    a = v.p(0.9, -0.3)
    c.saveState(); c.setFillColor(col); p = c.beginPath()
    p.moveTo(a[0], a[1]); p.lineTo(a[0] - 0.7, a[1] - 1.6); p.lineTo(a[0] + 0.7, a[1] - 1.6)
    p.close(); c.drawPath(p, fill=1, stroke=0); c.restoreState()
    px, py = v.p(2.0, 18.0)
    texto(c, px, py, 'PATIO POSTERIOR', 1.8, al='c', col=col)


def cotas_planta(c, v, pb=False):
    # horizontales al sur
    yb = -4.0 if pb else 0.0
    off1 = -9 if pb else -7
    for (a, b) in ((0, 2.6), (2.6, 4.8), (4.8, 8.0), (8.0, 10.0)):
        cota_h(c, v, a, b, yb, off1)
    cota_h(c, v, -2.0, 0.0, yb, off1)
    cota_h(c, v, -2.0, 10.0, yb, off1 - 5, '12.00')
    # verticales al oriente
    for (a, b) in ((0, 5.4), (5.4, 8.6), (8.6, 10.6), (10.6, 12.6), (12.6, 14.6), (14.6, 17.0)):
        cota_v(c, v, a, b, 10.0, 6)
    if pb:
        cota_v(c, v, -4.0, 0.0, 10.0, 6)
        cota_v(c, v, 17.0, 19.0, 10.0, 6)
        cota_v(c, v, -4.0, 19.0, 10.0, 11, '23.00')
    else:
        cota_v(c, v, 0.0, 17.0, 10.0, 11, '17.00')
    # al poniente
    for (a, b) in ((0, 5.4), (5.4, 7.4), (7.4, 10.6), (10.6, 12.6), (12.6, 17.0)):
        cota_v(c, v, a, b, 0.0 if not pb else -2.0, -6)


# ----------------------------------------------------------------------
#  LÁMINA A-01  PLANTAS ARQUITECTÓNICAS
# ----------------------------------------------------------------------
def lamina_A01(c):
    marco(c, 'A-01', ['Plantas arquitectónicas', 'Planta baja · Planta tipo', 'Planta de azotea'],
          '1:75 / 1:150', 1)
    v1 = Vista(42, 103, 75)
    exterior_pb(c, v1)
    planta_arq(c, v1, 0)
    cotas_planta(c, v1, True)
    titulo_dibujo(c, 30, 26, 'PLANTA BAJA  ·  Depto. 101', 'Esc. 1:75   N.P.T. ±0.00')
    norte(c, 172, 380)

    v2 = Vista(222, 103, 75)
    planta_arq(c, v2, 1)
    cotas_planta(c, v2, False)
    titulo_dibujo(c, 210, 26, 'PLANTA TIPO  ·  Niveles 1, 2 y 3',
                  'Esc. 1:75   Deptos. 201, 301 y 401   N.P.T. +3.00 / +6.00 / +9.00')
    # corte A-A'
    for vv, y0, y1 in ((v1, -4.6, 19.3), (v2, -1.0, 18.0)):
        linea_m(c, vv, [(6.5, y0), (6.5, y1)], 0.25, NEGRO, dash=(6, 1.5, 1, 1.5))
        for yy in (y0, y1):
            px, py = vv.p(6.5, yy)
            texto(c, px + 1.2, py + (0.8 if yy > 5 else -2.6), "A'" if yy > 5 else 'A',
                  2.8, 'Helvetica-Bold')

    # azotea
    v3 = Vista(385, 250, 150)
    rect_m(c, v3, 0, 0, 10, 17, stroke=NEGRO, w=0.35)
    rect_m(c, v3, 0.15, 0.15, 9.85, 16.85, stroke=NEGRO, w=0.1)
    rect_m(c, v3, 0, 0, 2.6, 5.4, fill=GRIS_MC, stroke=NEGRO, w=0.3)
    rect_m(c, v3, 8.0, 10.6, 10.0, 12.6, stroke=NEGRO, w=0.2)
    linea_m(c, v3, [(8.0, 10.6), (10.0, 12.6)], 0.1)
    linea_m(c, v3, [(8.0, 12.6), (10.0, 10.6)], 0.1)
    rect_m(c, v3, 4.8, 5.4, 5.6, 6.2, stroke=NEGRO, w=0.15)
    # pendientes hacia bajadas pluviales
    for (bx, by) in ((9.6, 0.4), (0.4, 16.6), (9.6, 16.6)):
        px, py = v3.p(bx, by)
        c.saveState(); lw(c, 0.15); c.circle(px, py, 0.9); c.restoreState()
    for (x0, y0, x1, y1) in ((6.0, 3.0, 8.8, 1.2), (3.0, 12.0, 1.2, 15.5), (7.0, 13.0, 8.8, 15.6)):
        linea_m(c, v3, [(x0, y0), (x1, y1)], 0.15)
        a = v3.p(x1, y1)
        c.saveState(); c.circle(a[0], a[1], 0.4, fill=1); c.restoreState()
    for (tx, ty, s) in ((1.3, 2.4, 'Caseta'), (1.3, 1.6, 'escalera'), (9.0, 11.4, 'Cubo'),
                        (5.6, 8.0, 'Losa impermeabilizada'), (5.6, 7.0, 'pend. 2 %'),
                        (5.2, 6.6, '')):
        px, py = v3.p(tx, ty)
        texto(c, px, py, s, 1.8, al='c')
    px, py = v3.p(5.2, 4.6)
    texto(c, px, py, 'Ventila ducto', 1.5, al='c')
    titulo_dibujo(c, 380, 228, 'PLANTA DE AZOTEA', 'Esc. 1:150   N.P.T. +12.00')
    parrafo(c, 380, 210, [
        '**Notas de azotea',
        '· No se proyectan tinacos: el suministro',
        '  es presurizado desde la cisterna',
        '  (ver lámina IH-04, revisión).',
        '· Bajadas pluviales Ø 100 mm (B.A.P.).',
        '· Pretil h = 0.90 m en todo el perímetro.',
        '· Calentadores de paso en lavandería',
        '  de cada depto., ventilados al cubo.',
    ], 2.1)
    # cuadro de áreas
    y = 160
    texto(c, 380, y, 'CUADRO DE ÁREAS POR DEPARTAMENTO', 2.4, 'Helvetica-Bold'); y -= 4
    filas = [('Local', 'm²')]
    tot = 0
    for (nom, x0, y0, x1, y1, tp) in CUARTOS:
        if nom in ('Escalera', 'Cubo de luz'):
            continue
        a = (x1 - x0) * (y1 - y0) - (0.64 if nom == 'Cocina' else 0)
        tot += a
        filas.append((nom, '%.2f' % a))
    filas.append(('Total interior (a ejes)', '%.2f' % tot))
    for i, (a, b) in enumerate(filas):
        f = 'Helvetica-Bold' if i in (0, len(filas) - 1) else 'Helvetica'
        texto(c, 382, y, a, 2.0, f)
        texto(c, 470, y, b, 2.0, f, 'r')
        c.saveState(); lw(c, 0.08); c.setStrokeColor(GRIS_C)
        c.line(380, y - 0.9, 472, y - 0.9); c.restoreState()
        y -= 3.2
    parrafo(c, 380, y - 3, [
        '**Programa por departamento',
        '3 recámaras (principal con vestidor y baño)',
        '2 baños completos + 1 medio baño = 2½ baños',
        'Sala-comedor, cocina integral, lavandería',
    ], 2.1)


# ----------------------------------------------------------------------
#  LÁMINA A-02  FACHADA Y CORTE
# ----------------------------------------------------------------------
def lamina_A02(c):
    marco(c, 'A-02', ['Fachada principal', "Corte longitudinal A-A'"], '1:100', 2)
    # ---------------- Fachada principal ----------------
    v = Vista(45, 175, 100)
    linea_m(c, v, [(-2.5, 0), (10.8, 0)], 0.5)
    for i in range(14):
        x = -2.4 + i * 0.95
        linea_m(c, v, [(x, 0), (x - 0.4, -0.4)], 0.08)
    rect_m(c, v, 0, 0, 10, 12.9, stroke=NEGRO, w=0.4)
    rect_m(c, v, 0, 12.9, 2.6, 14.7, stroke=NEGRO, w=0.4)
    rect_m(c, v, 0, 12.9, 10, 13.05, fill=GRIS_C, stroke=NEGRO, w=0.15)
    for i in range(1, 5):
        z = i * 3.0
        rect_m(c, v, 0, z - 0.2, 10, z, fill=GRIS_MC, stroke=NEGRO, w=0.12)
    for i in range(4):
        z = i * 3.0
        rect_m(c, v, 3.5, z + 0.9, 9.0, z + 2.4, fill=AZUL_C, stroke=NEGRO, w=0.25)
        for k in range(1, 5):
            xx = 3.5 + k * 1.1
            linea_m(c, v, [(xx, z + 0.9), (xx, z + 2.4)], 0.15)
        linea_m(c, v, [(3.5, z + 0.9), (9.0, z + 0.9)], 0.35)
        if i > 0:      # barandal/balcón francés
            for k in range(23):
                xx = 3.55 + k * 0.24
                linea_m(c, v, [(xx, z), (xx, z + 0.9)], 0.06)
            linea_m(c, v, [(3.5, z + 0.9), (9.0, z + 0.9)], 0.25)
    rect_m(c, v, 0.30, 0, 1.30, 2.4, fill=GRIS_MC, stroke=NEGRO, w=0.3)
    linea_m(c, v, [(0.8, 0), (0.8, 2.4)], 0.1)
    rect_m(c, v, 1.55, 2.8, 2.25, 14.2, fill=AZUL_C, stroke=NEGRO, w=0.25)
    for z in (3.0, 6.0, 9.0, 12.0):
        linea_m(c, v, [(1.55, z), (2.25, z)], 0.15)
    rect_m(c, v, 8.4, 0, 10.0, 2.2, fill=GRIS_MC, stroke=NEGRO, w=0.3)   # cuarto máquinas
    rect_m(c, v, 8.6, 0, 9.4, 2.0, stroke=NEGRO, w=0.15)
    for k in range(4):
        linea_m(c, v, [(8.6, 0.4 + k * 0.4), (9.4, 0.4 + k * 0.4)], 0.06)
    rect_m(c, v, CIS_X0 - 0.2, CIS_FONDO - 0.2, CIS_X1 + 0.2, 0.15, stroke=GRIS, w=0.2, dash=(2, 1))
    px, py = v.p(6.5, -1.4)
    texto(c, px, py, 'Cisterna (oculta)', 1.8, al='c', col=GRIS)
    for z, s in ((0, '±0.00 N.P.T. P.B.'), (3, '+3.00 N.P.T. N1'), (6, '+6.00 N.P.T. N2'),
                 (9, '+9.00 N.P.T. N3'), (12, '+12.00 Azotea'), (12.9, '+12.90 Pretil'),
                 (14.7, '+14.70 Caseta')):
        px, py = v.p(10.8, z)
        nivel_marca(c, px + 3, py, s)
    cota_v(c, v, 0, 3, 0, -8); cota_v(c, v, 3, 6, 0, -8); cota_v(c, v, 6, 9, 0, -8)
    cota_v(c, v, 9, 12, 0, -8); cota_v(c, v, 12, 12.9, 0, -8)
    cota_v(c, v, 0, 12.9, 0, -14, '12.90')
    cota_h(c, v, 0, 2.6, 0, -7); cota_h(c, v, 2.6, 10, 0, -7); cota_h(c, v, 0, 10, 0, -12, '10.00')
    for (x, z, s) in ((6.25, 10.2, 'Cancel aluminio natural, vidrio 6 mm'),
                      (6.25, 4.55, 'Barandal herrería h = 0.90'),
                      (5.0, 13.4, 'Pretil aplanado'),
                      (-1.1, 7.5, 'Muro aplanado')):
        px, py = v.p(x, z)
        texto(c, px, py, s, 1.7, al='c', rot=90 if x < 0 else 0)
    titulo_dibujo(c, 30, 122, 'FACHADA PRINCIPAL (SUR)', 'Esc. 1:100')

    # ---------------- Corte A-A' ----------------
    v = Vista(262, 175, 100)
    Y0, Y1 = -4.0, 19.0
    linea_m(c, v, [(Y0 - 0.5, 0), (CIS_Y0 - 0.2, 0)], 0.5)
    linea_m(c, v, [(CIS_Y1 + 0.2, 0), (Y1 + 0.5, 0)], 0.5)
    # terreno achurado
    for i in range(30):
        y = Y0 - 0.3 + i * 0.8
        if CIS_Y0 - 0.3 < y < CIS_Y1 + 0.3:
            continue
        linea_m(c, v, [(y, 0), (y - 0.4, -0.4)], 0.08)
    # losas
    rect_m(c, v, 0, -0.1, 17, 0.0, fill=GRIS, stroke=NEGRO, w=0.1)
    for i in range(1, 5):
        z = i * 3.0
        rect_m(c, v, -0.125, z - 0.2, 17.125, z, fill=GRIS, stroke=NEGRO, w=0.12)
    # relleno azotea y pretiles
    p = [v.p(0, 12.0), v.p(8.5, 12.25), v.p(17, 12.0)]
    linea_m(c, v, [(0, 12.0), (8.5, 12.25), (17, 12.0)], 0.12)
    rect_m(c, v, -0.125, 12.0, 0.125, 12.9, fill=GRIS, stroke=NEGRO, w=0.1)
    rect_m(c, v, 16.875, 12.0, 17.125, 12.9, fill=GRIS, stroke=NEGRO, w=0.1)
    # muros cortados en x = 6.5
    cortados = [(0.0, TE), (8.6, TI), (12.6, TI), (14.6, TI), (17.0, TE)]
    for i in range(4):
        z0, z1 = i * 3.0, i * 3.0 + 2.8
        for (yy, t) in cortados:
            if yy == 0.0:
                rect_m(c, v, yy - t / 2, z0, yy + t / 2, z0 + 0.9, fill=NEGRO, stroke=None)
                rect_m(c, v, yy - t / 2, z0 + 2.4, yy + t / 2, z1, fill=NEGRO, stroke=None)
                rect_m(c, v, yy - t / 2, z0 + 0.9, yy + t / 2, z0 + 2.4, stroke=NEGRO, w=0.12)
                linea_m(c, v, [(yy, z0 + 0.9), (yy, z0 + 2.4)], 0.12)
            else:
                rect_m(c, v, yy - t / 2, z0, yy + t / 2, z1, fill=NEGRO, stroke=None)
        # muros en elevación (sin cortar), puertas
        for (ya, yb) in ((9.0, 9.85),):
            pass
        nombres = [(2.7, 'Sala - comedor'), (7.0, 'Cocina'), (10.6, 'Recámara 3'),
                   (13.6, 'Baño ppal.'), (15.8, 'Vestidor')]
        for (yy, s) in nombres:
            px, py = v.p(yy, z0 + 1.1)
            texto(c, px, py, s, 1.9, al='c')
        px, py = v.p(2.7, z0 + 0.5)
        texto(c, px, py, DEPTOS[i], 1.6, al='c', col=GRIS)
        # plafón (línea punteada) donde corre la tubería
        linea_m(c, v, [(0.15, z0 + 2.7), (16.9, z0 + 2.7)], 0.08, GRIS, dash=(1.5, 1))
    # caseta escalera (en elevación, detrás del corte)
    rect_m(c, v, 0, 12.0, 5.4, 14.7, stroke=GRIS, w=0.2)
    # cimentación
    for (yy, t) in cortados:
        rect_m(c, v, yy - 0.5, -0.9, yy + 0.5, -0.6, stroke=GRIS, w=0.15, dash=(1.5, 1))
        rect_m(c, v, yy - t / 2, -0.6, yy + t / 2, -0.1, stroke=GRIS, w=0.15, dash=(1.5, 1))
    # cisterna en corte
    rect_m(c, v, CIS_Y0 - 0.2, CIS_FONDO - 0.2, CIS_Y1 + 0.2, 0.15, fill=GRIS, stroke=NEGRO, w=0.15)
    rect_m(c, v, CIS_Y0, CIS_FONDO, CIS_Y1, 0.0, fill=colors.white, stroke=NEGRO, w=0.12)
    rect_m(c, v, CIS_Y0, CIS_FONDO, CIS_Y1, CIS_AGUA, fill=AZUL_C, stroke=None)
    linea_m(c, v, [(CIS_Y0, CIS_AGUA), (CIS_Y1, CIS_AGUA)], 0.2, AZUL)
    px, py = v.p((CIS_Y0 + CIS_Y1) / 2, -1.5)
    texto(c, px, py, 'CISTERNA', 2.0, 'Helvetica-Bold', 'c')
    texto(c, px, py - 2.6, '%.1f m³' % V_CIS_UTIL, 1.8, al='c')
    # montante (oculto, detrás del corte)
    linea_m(c, v, [(-0.2, -0.3), (5.6, -0.3), (5.6, 11.6)], 0.35, AZUL, dash=(3, 1.2))
    px, py = v.p(5.75, 7.4)
    texto(c, px, py, 'Montante AF en ducto (oculto)', 1.6, col=AZUL, rot=90)
    for z, s in ((0, '±0.00'), (3, '+3.00'), (6, '+6.00'), (9, '+9.00'), (12, '+12.00'),
                 (12.9, '+12.90')):
        px, py = v.p(19.0, z)
        nivel_marca(c, px + 3, py, s)
    for z, s in ((CIS_AGUA, 'N.A.M. %.2f' % CIS_AGUA), (CIS_FONDO, 'Fondo %.2f' % CIS_FONDO)):
        px, py = v.p(CIS_Y0 - 0.3, z)
        nivel_marca(c, px, py, s, 1.7, izq=True)
    for i in range(4):
        cota_v(c, v, i * 3.0, i * 3.0 + 3.0, 17.0, 6)
    cota_v(c, v, 12.0, 12.9, 17.0, 6)
    cota_v(c, v, 0, 12.9, 17.0, 12, '12.90')
    for (a, b) in ((-4.0, 0.0), (0.0, 5.4), (5.4, 8.6), (8.6, 12.6), (12.6, 14.6), (14.6, 17.0), (17.0, 19.0)):
        cota_h(c, v, a, b, CIS_FONDO - 0.2, -6)
    cota_h(c, v, -4.0, 19.0, CIS_FONDO - 0.2, -11, '23.00')
    px, py = v.p(-3.6, 1.2)
    texto(c, px, py, 'Calle', 1.8)
    px, py = v.p(-3.6, 0.4)
    texto(c, px, py, 'Banqueta', 1.6)
    titulo_dibujo(c, 230, 122, "CORTE LONGITUDINAL A-A'", 'Esc. 1:100   (corte por el eje x = 6.50, viendo al poniente)')


# ----------------------------------------------------------------------
#  RED EN PLANTA (para IH-01)
# ----------------------------------------------------------------------
def red_en_planta(c, v, lev, rotular=True):
    """Dibuja la red AF de un nivel en planta y rotula diámetros."""
    s = '_%d' % lev
    hechos = set()
    for (p, h), inf in RED.info.items():
        if not h.endswith(s) or inf.get('tipo'):
            continue
        P, H = RED.n[p], RED.n[h]
        if abs(P['x'] - H['x']) < 1e-6 and abs(P['y'] - H['y']) < 1e-6:
            # bajada a mueble
            px, py = v.p(H['x'], H['y'])
            c.saveState(); c.setFillColor(AZUL); c.circle(px, py, 0.55, fill=1, stroke=0); c.restoreState()
            continue
        linea_m(c, v, [(P['x'], P['y']), (H['x'], H['y'])], 0.45, AZUL)
        if rotular and inf['L'] > 0.6:
            mx, my = (P['x'] + H['x']) / 2, (P['y'] + H['y']) / 2
            px, py = v.p(mx, my)
            horiz = abs(P['y'] - H['y']) < 1e-6
            lab = '%d' % inf['dn'][0]
            key = (round(mx, 1), round(my, 1))
            if key in hechos:
                continue
            hechos.add(key)
            if horiz:
                texto(c, px, py + 0.8, lab, 1.6, 'Helvetica-Bold', 'c', AZUL)
            else:
                texto(c, px - 0.8, py, lab, 1.6, 'Helvetica-Bold', 'c', AZUL, rot=90)
    # montante
    rx, ry = RISER_XY
    px, py = v.p(rx, ry)
    c.saveState(); lw(c, 0.35); c.setStrokeColor(AZUL); c.circle(px, py, 1.3)
    c.setFillColor(AZUL); c.circle(px, py, 0.5, fill=1); c.restoreState()
    # válvula + medidor
    a = v.p(5.0, 6.0)
    c.saveState(); lw(c, 0.2); c.setStrokeColor(AZUL); c.circle(a[0], a[1], 0.8); c.restoreState()
    texto(c, a[0], a[1] - 0.55, 'M', 1.3, 'Helvetica-Bold', 'c', AZUL)


def planta_hid(c, v, lev, pb):
    if pb:
        exterior_pb(c, v, 'hid')
    planta_arq(c, v, 0 if pb else 1, 'hid')
    red_en_planta(c, v, lev)
    # etiquetas de muebles
    for (x, y, s, dx, dy) in ((2.25, 7.05, 'W.C.', -1.0, -0.7), (3.1, 7.05, 'Lav.', 0.3, -0.7),
                              (2.7, 12.2, 'Lav.', 0.0, -0.65), (1.75, 12.2, 'W.C.', 0.0, -0.65),
                              (0.55, 12.2, 'Reg.', 0.0, -0.65), (6.6, 13.0, 'Lav.', 0.0, 0.4),
                              (7.7, 13.0, 'W.C.', 0.0, 0.4), (9.8, 13.8, 'Reg.', -0.65, 0.25),
                              (9.75, 7.2, 'Freg.', -0.8, 0.0), (9.75, 9.2, 'Ldro.', -0.8, 0.0),
                              (9.75, 10.1, 'Lavad.', -0.85, -0.1), (8.4, 10.35, 'Cal.', 0.0, -0.6)):
        px, py = v.p(x + dx, y + dy)
        texto(c, px, py, s, 1.45, al='c', col=AZUL)
    rx, ry = RISER_XY
    px, py = v.p(rx + 0.25, ry - 0.55)
    texto(c, px, py, 'S.A.F.', 1.5, 'Helvetica-Bold', col=AZUL)
    if pb:
        # línea principal enterrada, equipo, toma
        pts = [(9.5, -1.2), (9.5, -0.2), (5.0, -0.2), (5.0, 5.6)]
        linea_m(c, v, pts, 0.6, AZUL, dash=(3, 1))
        px, py = v.p(7.3, -0.05)
        texto(c, px, py, 'Línea enterrada Ø %d mm' % RED.info[('P2', 'P3')]['dn'][0], 1.6,
              'Helvetica-Bold', 'c', AZUL)
        # succión
        linea_m(c, v, [(7.6, -2.0), (8.75, -2.0)], 0.5, AZUL)
        # bombas
        for yy in (-2.6, -1.6):
            px, py = v.p(9.1, yy)
            c.saveState(); lw(c, 0.25); c.setStrokeColor(AZUL); c.circle(px, py, 2.4); c.restoreState()
        px, py = v.p(9.1, -2.62); texto(c, px, py - 0.6, 'B-1', 1.5, 'Helvetica-Bold', 'c', AZUL)
        px, py = v.p(9.1, -1.62); texto(c, px, py - 0.6, 'B-2', 1.5, 'Helvetica-Bold', 'c', AZUL)
        linea_m(c, v, [(8.75, -2.6), (8.75, -1.6)], 0.4, AZUL)
        linea_m(c, v, [(9.5, -2.6), (9.5, -1.2)], 0.4, AZUL)
        px, py = v.p(9.6, -3.2)
        c.saveState(); lw(c, 0.25); c.setStrokeColor(AZUL); c.circle(px, py, 1.6); c.restoreState()
        texto(c, px, py - 0.6, 'T', 1.4, 'Helvetica-Bold', 'c', AZUL)
        # toma
        linea_m(c, v, [(9.0, -4.0), (9.0, -3.75), (7.7, -3.75), (7.7, -3.0)], 0.45, VERDE)
        px, py = v.p(9.0, -4.0)
        c.saveState(); lw(c, 0.25); c.setStrokeColor(VERDE); c.rect(px - 1.6, py - 1.0, 3.2, 2.0); c.restoreState()
        texto(c, px + 2.2, py - 2.6, 'Toma municipal + medidor Ø 19 mm', 1.6, 'Helvetica-Bold', 'l', VERDE)
        px, py = v.p(7.7, -3.0)
        texto(c, px - 0.5, py + 0.4, 'V.F.', 1.4, 'Helvetica-Bold', 'r', VERDE)


def leyenda_hid(c, x, y):
    texto(c, x, y, 'SIMBOLOGÍA', 2.6, 'Helvetica-Bold'); y -= 5
    items = [
        ('lin', AZUL, None, 'Tubería de agua fría (AF), por plafón'),
        ('lin', AZUL, (3, 1), 'Tubería AF enterrada (bajo piso)'),
        ('lin', ROJO, (2, 1), 'Tubería de agua caliente (AC)'),
        ('lin', VERDE, None, 'Toma municipal / llenado de cisterna'),
        ('pto', AZUL, None, 'Bajada a mueble (salida)'),
        ('sub', AZUL, None, 'S.A.F. Subida de agua fría (montante)'),
        ('med', AZUL, None, 'Válvula de compuerta + medidor'),
        ('txt', AZUL, None, '25  = diámetro nominal en mm'),
    ]
    for tipo, col, dash, s in items:
        c.saveState(); c.setStrokeColor(col); c.setFillColor(col); lw(c, 0.5)
        if tipo == 'lin':
            if dash:
                c.setDash(list(dash), 0)
            c.line(x, y + 0.8, x + 10, y + 0.8)
        elif tipo == 'pto':
            c.circle(x + 5, y + 0.8, 0.6, fill=1, stroke=0)
        elif tipo == 'sub':
            lw(c, 0.3); c.circle(x + 5, y + 0.8, 1.3); c.circle(x + 5, y + 0.8, 0.5, fill=1)
        elif tipo == 'med':
            lw(c, 0.2); c.circle(x + 5, y + 0.8, 1.0)
        c.restoreState()
        if tipo == 'med':
            texto(c, x + 5, y + 0.25, 'M', 1.3, 'Helvetica-Bold', 'c', AZUL)
        if tipo == 'txt':
            texto(c, x + 5, y + 0.3, '25', 1.8, 'Helvetica-Bold', 'c', AZUL)
            s = s[4:]
        texto(c, x + 13, y, s, 2.0)
        y -= 4.2
    return y


def lamina_IH01(c):
    marco(c, 'IH-01', ['Instalación hidráulica', 'Agua potable en planta', 'P.B. y planta tipo'],
          '1:75', 3)
    v1 = Vista(42, 103, 75)
    planta_hid(c, v1, 0, True)
    cotas_planta(c, v1, True)
    titulo_dibujo(c, 30, 26, 'INST. HIDRÁULICA  ·  PLANTA BAJA', 'Esc. 1:75   Cisterna, equipo de bombeo, línea principal y Depto. 101')
    v2 = Vista(222, 103, 75)
    planta_hid(c, v2, 3, False)
    cotas_planta(c, v2, False)
    titulo_dibujo(c, 210, 26, 'INST. HIDRÁULICA  ·  PLANTA TIPO (N1 a N3)',
                  'Esc. 1:75   Deptos. 201, 301 y 401 (red idéntica en los tres niveles)')
    norte(c, 172, 380)
    y = leyenda_hid(c, 380, 392)
    y -= 4
    parrafo(c, 380, y, [
        '**Notas de instalación hidráulica',
        '1. La red de cada departamento corre por plafón',
        '   (+2.60 sobre N.P.T.) y baja a cada mueble',
        '   ahogada en muro.',
        '2. Cada departamento tiene en el ducto: válvula',
        '   de compuerta, medidor individual Ø 25 mm y',
        '   válvula check.',
        '3. Alturas de salidas sobre N.P.T.: W.C. 0.25,',
        '   lavabo y fregadero 0.55, lavadero y lavadora',
        '   1.00, mezcladora de regadera 1.10, brazo de',
        '   regadera 1.90, calentador 1.50.',
        '4. Colocar cámara de aire (Ø 13 x 0.40 m) en',
        '   cada salida, y válvula de paso en cada mueble.',
        '5. Agua caliente: ver isométrico IH-03.',
        '6. Cisterna a 1.80 m de la colindancia y a más',
        '   de 3.00 m de albañales y registros sanitarios.',
        '7. La red de cada nivel es la misma; los',
        '   diámetros indicados aplican a los 4 deptos.',
        '',
        '**Diámetros en planta (mm)',
        '   13 = 1/2"   19 = 3/4"   25 = 1"',
        '   32 = 1 1/4"   38 = 1 1/2"   50 = 2"',
    ], 2.05)


# ----------------------------------------------------------------------
#  ISOMÉTRICOS
# ----------------------------------------------------------------------
C30 = math.cos(math.radians(30))


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


def dibujar_red_iso(c, I, niveles=(0, 1, 2, 3), rot_niveles=(3,), solo_depto=None,
                    t=1.7, ac=False):
    """Dibuja la red AF en isométrico. Si solo_depto, dibuja sólo ese nivel
    (en coordenadas locales, lev=0)."""
    for (p, h), inf in RED.info.items():
        P, H = RED.n[p], RED.n[h]
        if solo_depto is not None:
            if not (h.endswith('_%d' % solo_depto)) or inf.get('tipo'):
                continue
            lp = lh = 0
        else:
            if P['lev'] not in niveles and H['lev'] not in niveles:
                continue
            lp, lh = P['lev'], H['lev']
        a = (P['x'], P['y'], P['z'], lp)
        b = (H['x'], H['y'], H['z'], lh)
        tipo = inf.get('tipo')
        wid = 0.75 if tipo in ('principal', 'montante') else 0.45
        dash = (3, 1) if tipo == 'principal' and P['z'] < 0 and H['z'] < 0 else None
        iso_linea(c, I, [a, b], wid, AZUL, dash)
        if inf.get('medidor'):
            pa, pb = I.p(*a), I.p(*b)
            ang = ang_iso(I, a, b)
            valvula(c, pa[0] + (pb[0] - pa[0]) * 0.3, pa[1] + (pb[1] - pa[1]) * 0.3, ang, s=0.9)
            medidor(c, pa[0] + (pb[0] - pa[0]) * 0.68, pa[1] + (pb[1] - pa[1]) * 0.68, r=1.15)
        # rótulos de diámetro
        rot = (solo_depto is not None) or (lh in rot_niveles) or tipo in ('principal', 'montante')
        if rot and inf['L'] > 0.45 and tipo != 'aire' and not H['fix']:
            pa, pb = I.p(*a), I.p(*b)
            mx, my = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
            ang = ang_iso(I, a, b)
            if ang > 90:
                ang -= 180
            if ang < -90:
                ang += 180
            vert = abs(abs(ang) - 90) < 1
            s = 'Ø%d' % inf['dn'][0]
            if vert:
                texto(c, mx - 0.6, my, s, t, 'Helvetica-Bold', 'c', AZUL, rot=90)
            else:
                c.saveState(); c.translate(mx, my); c.rotate(ang)
                texto(c, 0, 0.6, s, t, 'Helvetica-Bold', 'c', AZUL)
                c.restoreState()
        # muebles
        if H['fix']:
            q = I.p(*b)
            c.saveState(); c.setFillColor(AZUL); c.circle(q[0], q[1], 0.55, fill=1, stroke=0); c.restoreState()
            if solo_depto is not None or lh in rot_niveles:
                texto(c, q[0], q[1] - 2.4, ABREV[H['fix']], t * 0.95, 'Helvetica', 'c', NEGRO)


def red_ac(lev=0):
    """Polilíneas de agua caliente (local)."""
    zc = Z_PLAFON_AC
    H0 = (8.55, 10.35)
    segs = [
        [(8.55, 10.35, 1.60), (8.55, 10.35, zc)],
        [(8.55, 10.35, zc), (8.55, 7.35, zc), (9.6, 7.35, zc), (9.6, 7.35, 0.55)],
        [(8.55, 10.35, zc), (7.8, 10.35, zc), (7.8, 12.9, zc), (9.9, 12.9, zc), (9.9, 13.7, zc),
         (9.9, 13.7, 1.10)],
        [(7.8, 12.9, zc), (4.35, 12.9, zc), (4.35, 12.1, zc), (0.55, 12.1, zc), (0.55, 12.1, 1.10)],
        [(6.6, 12.9, zc), (6.6, 12.9, 0.55)],
        [(2.7, 12.1, zc), (2.7, 12.1, 0.55)],
        [(4.35, 12.1, zc), (4.35, 7.2, zc), (3.1, 7.2, zc), (3.1, 7.2, 0.55)],
    ]
    return segs


def iso_cisterna_equipo(c, I, det):
    """Cisterna, llenado, succión y equipo de bombeo en isométrico.
    det=True: versión de detalle con todos los rótulos."""
    t = 2.0 if det else 1.6
    iso_caja(c, I, CIS_X0, CIS_Y0, CIS_FONDO, CIS_X1, CIS_Y1, 0.0, NEGRO, 0.2)
    pa = [I.p(CIS_X0, CIS_Y0, CIS_AGUA), I.p(CIS_X1, CIS_Y0, CIS_AGUA),
          I.p(CIS_X1, CIS_Y1, CIS_AGUA), I.p(CIS_X0, CIS_Y1, CIS_AGUA)]
    c.saveState(); c.setFillColor(AZUL_C); c.setStrokeColor(AZUL); lw(c, 0.2)
    p = c.beginPath(); p.moveTo(*pa[0])
    for q in pa[1:]:
        p.lineTo(*q)
    p.close(); c.drawPath(p, fill=1, stroke=1); c.restoreState()
    iso_caja(c, I, CIS_X0, CIS_Y0, CIS_FONDO, CIS_X1, CIS_Y1, 0.0, NEGRO, 0.25 if det else 0.2)
    iso_caja(c, I, 7.4, -2.2, CIS_FONDO - 0.3, 7.8, -1.8, CIS_FONDO, GRIS, 0.12)
    iso_caja(c, I, 5.3, -2.9, 0.0, 5.9, -2.3, 0.15, NEGRO, 0.15)
    # succión
    iso_linea(c, I, [(7.6, -2.0, CIS_FONDO - 0.15), (7.6, -2.0, 0.30), (8.75, -2.0, 0.30)],
              0.8 if det else 0.6, AZUL)
    # llenado
    iso_linea(c, I, [(9.0, -4.0, -0.40), (9.0, -3.75, -0.40), (7.7, -3.75, -0.40), (7.7, -3.0, -0.40),
                     (7.7, -3.0, -0.55)], 0.55 if det else 0.45, VERDE)
    q = I.p(9.0, -4.0, -0.40)
    medidor(c, q[0], q[1], VERDE, 1.6 if det else 1.2)
    # equipo
    for yy, nb in ((-2.6, 'B-1'), (-1.6, 'B-2')):
        iso_linea(c, I, [(8.75, yy, 0.30), (9.5, yy, 0.30)], 0.8 if det else 0.6, AZUL)
    iso_linea(c, I, [(8.75, -2.6, 0.30), (8.75, -1.6, 0.30)], 0.8 if det else 0.6, AZUL)
    iso_linea(c, I, [(9.5, -2.6, 0.30), (9.5, -1.2, 0.30)], 0.8 if det else 0.6, AZUL)
    iso_linea(c, I, [(9.5, -2.6, 0.30), (9.5, -3.15, 0.30)], 0.6, AZUL)
    for yy, nb in ((-2.6, 'B-1'), (-1.6, 'B-2')):
        q = I.p(9.1, yy, 0.30)
        r = 3.0 if det else 1.6
        c.saveState(); c.setFillColor(colors.white); c.setStrokeColor(AZUL); lw(c, 0.3)
        c.circle(q[0], q[1], r, fill=1); c.restoreState()
        texto(c, q[0], q[1] - 0.6, nb, 2.0 if det else 1.3, 'Helvetica-Bold', 'c', AZUL)
    q = I.p(9.5, -3.15, 0.30)
    hT, wT = (12.0, 5.0) if det else (5.0, 2.6)
    c.saveState(); c.setFillColor(colors.white); c.setStrokeColor(AZUL); lw(c, 0.3)
    c.roundRect(q[0] - wT / 2, q[1], wT, hT, wT / 2 - 0.1, fill=1); c.restoreState()
    texto(c, q[0], q[1] + hT / 2 - 0.6, 'T', 2.0 if det else 1.4, 'Helvetica-Bold', 'c', AZUL)
    iso_caja(c, I, 8.4, -3.5, 0.0, 10.0, -0.5, 2.2, GRIS, 0.12, (1.5, 1))
    if not det:
        q = I.p(CIS_X1, CIS_Y0, CIS_FONDO)
        texto(c, q[0] + 3, q[1] - 2, 'Cisterna y equipo de bombeo:', 1.8, 'Helvetica-Bold')
        texto(c, q[0] + 3, q[1] - 4.6, 'ver detalle isométrico (derecha)', 1.8)
        return
    # ------- detalle: descarga, accesorios y rótulos -------
    iso_linea(c, I, [(9.5, -1.2, 0.30), (9.5, -0.2, 0.30), (9.5, -0.2, -0.30), (7.0, -0.2, -0.30)],
              0.8, AZUL)
    iso_linea(c, I, [(7.0, -0.2, -0.30), (6.0, -0.2, -0.30)], 0.8, AZUL, (3, 1.2))
    for (x, y, z, ang) in ((9.5, -1.5, 0.3, None), (9.5, -2.2, 0.3, None)):
        q = I.p(x, y, z)
        valvula(c, q[0], q[1], ang_iso(I, (9.5, -2.6, 0.3), (9.5, -1.2, 0.3)), AZUL, 1.1)
    for yy in (-2.6, -1.6):
        q = I.p(9.35, yy, 0.30)
        valvula(c, q[0], q[1], ang_iso(I, (8.75, yy, 0.3), (9.5, yy, 0.3)), AZUL, 1.0)
    # manómetro
    q = I.p(9.5, -0.7, 0.30)
    c.saveState(); lw(c, 0.2); c.setStrokeColor(NEGRO); c.line(q[0], q[1], q[0], q[1] + 4)
    c.setFillColor(colors.white); c.circle(q[0], q[1] + 5.2, 1.3, fill=1); c.restoreState()
    def rot(x, y, z, s, dx, dy, al='l', col=NEGRO, b=False):
        q = I.p(x, y, z)
        c.saveState(); lw(c, 0.1); c.setStrokeColor(GRIS)
        c.line(q[0], q[1], q[0] + dx, q[1] + dy); c.restoreState()
        texto(c, q[0] + dx + (0.8 if al == 'l' else -0.8), q[1] + dy - 0.6, s, t,
              'Helvetica-Bold' if b else 'Helvetica', al, col)
    rot(9.5, -0.7, 0.30, 'Manómetro y transductor de presión', 22, 22)
    rot(9.5, -3.15, 0.9, 'T: tanque precargado 80 L', 18, 6)
    rot(9.1, -1.6, 0.30, 'B-2  %g HP (reserva, alterna)' % HP_COM, 26, 12)
    rot(9.1, -2.6, 0.30, 'B-1  %g HP con variador' % HP_COM, 26, -4)
    rot(9.5, -1.85, 0.30, 'Válv. check + compuerta', 22, -14)
    rot(8.4, -3.5, 2.2, 'Cuarto de máquinas 1.60 x 3.00 m', 10, 10, b=True)
    rot(6.5, -0.2, -0.30, 'Línea enterrada Ø %d a montante' % RED.info[('P2', 'P3')]['dn'][0],
        -8, 18, 'r', AZUL, True)
    rot(9.0, -4.0, -0.40, 'Toma municipal Ø 19 mm con medidor', 4, -14, 'l', VERDE, True)
    rot(7.7, -3.0, -0.55, 'Válvula de flotador Ø 19', -10, -26, 'r', VERDE)
    rot(7.6, -2.0, CIS_FONDO - 0.15, 'Pichancha / válvula de pie', 6, -16, 'l', AZUL)
    rot(7.6, -2.0, -0.9, 'Succión Ø 50', 10, -3, 'l', AZUL, True)
    rot(7.6, -2.0, CIS_FONDO - 0.3, 'Cárcamo 0.40 x 0.40 x 0.30', -14, -14, 'r')
    rot(5.6, -2.6, 0.15, 'Registro 0.60 x 0.60 hermético', -2, 30, 'r')
    # ventilación y electroniveles
    iso_linea(c, I, [(5.6, -1.0, 0.0), (5.6, -1.0, 1.0)], 0.4, GRIS)
    rot(5.6, -1.0, 1.0, 'Tubo de ventilación Ø 50 con malla', -4, 6, 'r')
    for zz in (CIS_AGUA - 0.1, Z_SUCC_MIN):
        iso_linea(c, I, [(6.6, -1.2, 0.0), (6.6, -1.2, zz)], 0.12, GRIS)
        q = I.p(6.6, -1.2, zz)
        c.saveState(); lw(c, 0.2); c.circle(q[0], q[1], 0.9); c.restoreState()
    rot(6.6, -1.2, Z_SUCC_MIN, 'Electronivel: paro por bajo nivel', -22, -2, 'r')
    rot(6.6, -1.2, CIS_AGUA - 0.1, 'Electronivel: alarma nivel alto', -22, 4, 'r')
    rot(CIS_X0, CIS_Y1, CIS_AGUA, 'N.A.M. %.2f' % CIS_AGUA, -8, 0, 'r', AZUL)
    rot(CIS_X0, CIS_Y1, CIS_FONDO, 'Fondo %.2f' % CIS_FONDO, -8, 0, 'r')
    rot(CIS_X0, CIS_Y1, 0.0, '±0.00 N.T.N.', -8, 0, 'r')


def lamina_IH02(c):
    marco(c, 'IH-02', ['Isométrico general', 'de agua potable', 'Cisterna · equipo · montante'],
          'Sin escala', 4)
    I = Iso(178, 62, 6.2, 12.5)
    for lev in range(4):
        pts = [(0, 0, 0, lev), (10, 0, 0, lev), (10, 17, 0, lev), (0, 17, 0, lev), (0, 0, 0, lev)]
        iso_linea(c, I, pts, 0.12, GRIS_C, (2, 1.5))
    iso_cisterna_equipo(c, I, False)
    dibujar_red_iso(c, I)
    rx, ry = RISER_XY
    q = I.p(rx, ry, 3.30, 3)
    c.saveState(); c.setFillColor(colors.white); c.setStrokeColor(AZUL); lw(c, 0.3)
    c.rect(q[0] - 0.9, q[1], 1.8, 2.0, fill=1); c.restoreState()
    c.saveState(); lw(c, 0.1); c.setStrokeColor(GRIS); c.line(q[0], q[1] + 2, q[0] + 30, q[1] - 4)
    c.restoreState()
    texto(c, q[0] + 31, q[1] - 4.6, 'Eliminador de aire Ø 13 mm (punto alto del montante)', 1.8, col=AZUL)
    for lev in range(4):
        q = I.p(rx, ry, Z_PLAFON, lev)
        txt = '%s  N.P.T. %s' % (NIVELES[lev], ['±0.00', '+3.00', '+6.00', '+9.00'][lev])
        x0 = 26
        c.saveState(); lw(c, 0.12); c.setStrokeColor(GRIS); c.setDash(1, 1)
        c.line(x0 + 55, q[1], q[0] - 2, q[1]); c.restoreState()
        texto(c, x0, q[1] + 2.0, txt, 2.6, 'Helvetica-Bold')
        texto(c, x0, q[1] - 1.4, '%s · %d UM · Q = %.2f L/s' % (
            DEPTOS[lev], UM_DEPTO, RED.info[('R%d' % lev, 'A_%d' % lev)]['q']), 2.0)
        pr = min(presion_salida(k) for k in FIXT if k.endswith('_%d' % lev))
        texto(c, x0, q[1] - 4.4, 'Presión mín. en salidas: %.1f m.c.a.' % pr, 2.0, col=AZUL)
    texto(c, 26, 388, 'ISOMÉTRICO GENERAL DE AGUA POTABLE', 4.2, 'Helvetica-Bold')
    texto(c, 26, 382, 'Sin escala · altura de entrepiso ampliada para claridad · '
          'diámetros rotulados en el Nivel 3 (los 4 niveles son idénticos) · bajadas a muebles Ø 13 mm', 2.1)
    leyenda_hid(c, 380, 392)
    # ------- detalle cisterna + equipo -------
    D = Iso(197, 128, 22, 0)
    iso_cisterna_equipo(c, D, True)
    titulo_dibujo(c, 300, 318, 'DETALLE ISOMÉTRICO: CISTERNA Y EQUIPO', 'Sin escala')
    parrafo(c, 300, 66, [
        '**CISTERNA',
        'Interior %.2f x %.2f m · tirante útil %.2f m' % (CIS_X1 - CIS_X0, CIS_Y1 - CIS_Y0, CIS_AGUA - CIS_FONDO),
        'Volumen útil %.2f m³ (requerido %.2f m³)' % (V_CIS_UTIL, V_CIS_REQ),
        'Concreto impermeable f\'c = 250 kg/cm²',
        'Tapa 0.15 sobre N.T.N. · ver detalles IH-03',
    ], 2.0)
    parrafo(c, 385, 66, [
        '**EQUIPO DE BOMBEO',
        '2 bombas centrífugas de %g HP, alternadas' % HP_COM,
        'Variador: presión constante %.1f kg/cm²' % (P_CONSIGNA / 10),
        'Q diseño %.2f L/s · CDT %.1f m' % (Q_TOTAL, CDT),
        'Paro automático por bajo nivel en cisterna',
    ], 2.0)


def lamina_IH03(c):
    marco(c, 'IH-03', ['Isométrico departamento tipo', '(agua fría y caliente)', 'Detalles de cisterna'],
          'Sin escala / 1:35', 5)
    I = Iso(250, 100, 15, 0)
    # contorno de muros (tenue) a nivel de piso
    for (o, k, a, b, t, vanos) in muros(1):
        if o == 'h':
            if k >= 5.4:
                iso_linea(c, I, [(a, k, 0), (b, k, 0)], 0.12, GRIS_C)
        elif b > 5.4:
            iso_linea(c, I, [(k, max(a, 5.4), 0), (k, b, 0)], 0.12, GRIS_C)
    for (nom, x0, y0, x1, y1, tp) in CUARTOS:
        if nom in ('Escalera', 'Sala - comedor', 'Clóset', 'Pasillo', 'Recámara 2', 'Recámara 3',
                   'Recámara principal', 'Vestidor', 'Cubo de luz'):
            continue
        q = I.p(tp[0], tp[1], 0)
        texto(c, q[0], q[1], nom, 1.8, al='c', col=GRIS)
    # AC
    for seg in red_ac():
        iso_linea(c, I, seg, 0.45, ROJO, (2.2, 1))
        if seg[-1][2] < 2.0 and len(seg) >= 2:
            q = I.p(*seg[-1])
            c.saveState(); c.setFillColor(ROJO); c.circle(q[0], q[1], 0.5, fill=1, stroke=0); c.restoreState()
    for (a, b, s) in (((8.55, 9.0, Z_PLAFON_AC), (8.55, 8.0, Z_PLAFON_AC), 'AC Ø19'),
                      ((6.0, 12.9, Z_PLAFON_AC), (5.0, 12.9, Z_PLAFON_AC), 'AC Ø19'),
                      ((4.35, 10.0, Z_PLAFON_AC), (4.35, 9.0, Z_PLAFON_AC), 'AC Ø13'),
                      ((1.8, 12.1, Z_PLAFON_AC), (1.2, 12.1, Z_PLAFON_AC), 'AC Ø13')):
        pa, pb = I.p(*a), I.p(*b)
        ang = ang_iso(I, a, b)
        if ang > 90: ang -= 180
        if ang < -90: ang += 180
        c.saveState(); c.translate((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2); c.rotate(ang)
        texto(c, 0, -2.4, s, 1.7, 'Helvetica-Bold', 'c', ROJO); c.restoreState()
    # AF
    dibujar_red_iso(c, I, solo_depto=3, t=1.8)
    # riser
    rx, ry = RISER_XY
    iso_linea(c, I, [(rx, ry, -0.6), (rx, ry, 3.3)], 0.9, AZUL)
    q = I.p(rx, ry, 3.3)
    texto(c, q[0] + 1.5, q[1] + 0.8, 'Montante AF (viene de la cisterna)', 1.8, 'Helvetica-Bold', col=AZUL)
    # alturas de salidas
    for nom in ('WCmb_3', 'LAVmb_3', 'REGbp_3', 'FRE_3', 'LDR_3', 'CAL_3', 'REGb2_3'):
        d = RED.n[nom]
        q = I.p(d['x'], d['y'], d['z'])
        texto(c, q[0] + 1.0, q[1] + 0.4, '+%.2f' % d['z'], 1.5, col=GRIS)
    q = I.p(8.4, 10.35, 1.5)
    c.saveState(); c.setFillColor(colors.white); c.setStrokeColor(NEGRO); lw(c, 0.3)
    c.roundRect(q[0] - 1.6, q[1] - 1.0, 3.2, 4.2, 0.6, fill=1); c.restoreState()
    texto(c, q[0] - 2.2, q[1] + 3.0, 'Calentador de paso', 1.7, 'Helvetica-Bold', 'r')
    texto(c, q[0] - 2.2, q[1] + 0.9, '16 L/min (gas)', 1.6, al='r')
    texto(c, 24, 388, 'ISOMÉTRICO DEPARTAMENTO TIPO  (Deptos. 101 a 401)', 4.0, 'Helvetica-Bold')
    texto(c, 24, 382, 'Sin escala · AF azul continuo · AC rojo discontinuo · diámetros nominales en mm', 2.2)
    # leyenda rápida
    parrafo(c, 24, 372, [
        '**Diámetros (cobre tipo M)',
        '13 = 1/2"   19 = 3/4"   25 = 1"   32 = 1 1/4"',
        '',
        '**Abreviaturas',
        'W.C. inodoro de tanque · Lav. lavabo',
        'Reg. regadera · Freg. fregadero',
        'Ldro. lavadero · Lavad. lavadora',
        'Cal. calentador · M medidor',
    ], 2.0)

    # ---------------- Detalle cisterna: planta ----------------
    v = Vista(362, 275, 35)
    x0, y0 = CIS_X0 - 0.2, CIS_Y0 - 0.2
    # desplazar para que el origen sea la esquina exterior
    vv = Vista(v.ox - x0 * v.k, v.oy - y0 * v.k, 35)
    rect_m(c, vv, CIS_X0 - 0.2, CIS_Y0 - 0.2, CIS_X1 + 0.2, CIS_Y1 + 0.2, fill=GRIS_C, stroke=NEGRO, w=0.3)
    rect_m(c, vv, CIS_X0, CIS_Y0, CIS_X1, CIS_Y1, fill=AZUL_C, stroke=NEGRO, w=0.2)
    rect_m(c, vv, 5.3, -2.9, 5.9, -2.3, fill=colors.white, stroke=NEGRO, w=0.25)
    texto(c, *vv.p(5.6, -2.68), 'Registro', 1.6, al='c')
    texto(c, *vv.p(5.6, -2.82), '0.60x0.60', 1.4, al='c')
    rect_m(c, vv, 7.4, -2.2, 7.8, -1.8, fill=colors.white, stroke=NEGRO, w=0.2, dash=(1.5, 1))
    texto(c, *vv.p(7.6, -1.68), 'Cárcamo', 1.6, al='c')
    texto(c, *vv.p(7.6, -2.42), '0.40x0.40x0.30', 1.4, al='c')
    px, py = vv.p(7.6, -2.0)
    c.saveState(); c.setFillColor(AZUL); c.circle(px, py, 0.9, fill=1, stroke=0); c.restoreState()
    linea_m(c, vv, [(7.6, -2.0), (8.2, -2.0)], 0.6, AZUL)
    texto(c, *vv.p(8.25, -1.9), 'Succión', 1.6, col=AZUL)
    linea_m(c, vv, [(8.2, -3.0), (7.7, -3.0)], 0.5, VERDE)
    texto(c, *vv.p(8.25, -3.05), 'Llenado', 1.6, col=VERDE)
    px, py = vv.p(6.6, -1.2)
    c.saveState(); lw(c, 0.2); c.circle(px, py, 0.8); c.restoreState()
    texto(c, *vv.p(6.6, -1.05), 'Electroniveles', 1.4, al='c')
    px, py = vv.p(5.6, -1.0)
    c.saveState(); lw(c, 0.2); c.circle(px, py, 0.7); c.restoreState()
    texto(c, *vv.p(5.6, -0.9), 'Ventila', 1.4, al='c')
    cota_h(c, vv, CIS_X0, CIS_X1, CIS_Y0 - 0.2, -5)
    cota_h(c, vv, CIS_X0 - 0.2, CIS_X1 + 0.2, CIS_Y0 - 0.2, -10)
    cota_v(c, vv, CIS_Y0, CIS_Y1, CIS_X1 + 0.2, 5)
    cota_v(c, vv, CIS_Y0 - 0.2, CIS_Y1 + 0.2, CIS_X1 + 0.2, 10)
    linea_m(c, vv, [(CIS_X0 - 0.5, -2.0), (CIS_X1 + 0.5, -2.0)], 0.2, NEGRO, (5, 1, 1, 1))
    texto(c, *vv.p(CIS_X0 - 0.55, -1.95), 'B', 2.6, 'Helvetica-Bold', 'r')
    texto(c, *vv.p(CIS_X1 + 0.55, -1.95), "B'", 2.6, 'Helvetica-Bold')
    titulo_dibujo(c, 345, 259, 'DETALLE CISTERNA · PLANTA', 'Esc. 1:35')

    # ---------------- Detalle cisterna: corte B-B' ----------------
    v = Vista(372, 135, 35)
    vv = Vista(v.ox - (CIS_X0 - 0.2) * v.k, v.oy - (CIS_FONDO - 0.2) * v.k, 35)
    X0, X1 = CIS_X0, CIS_X1
    rect_m(c, vv, X0 - 0.2, CIS_FONDO - 0.2, X1 + 0.2, 0.15, fill=GRIS_C, stroke=NEGRO, w=0.3)
    rect_m(c, vv, X0, CIS_FONDO, X1, 0.0, fill=colors.white, stroke=NEGRO, w=0.2)
    rect_m(c, vv, X0, CIS_FONDO, X1, CIS_AGUA, fill=AZUL_C, stroke=None)
    linea_m(c, vv, [(X0, CIS_AGUA), (X1, CIS_AGUA)], 0.25, AZUL)
    rect_m(c, vv, 7.4, CIS_FONDO - 0.3, 7.8, CIS_FONDO, fill=AZUL_C, stroke=NEGRO, w=0.2)
    rect_m(c, vv, 7.4, CIS_FONDO - 0.5, 7.8, CIS_FONDO - 0.3, fill=GRIS_C, stroke=None)
    # registro (hueco en tapa)
    rect_m(c, vv, 5.3, 0.0, 5.9, 0.15, fill=colors.white, stroke=NEGRO, w=0.15)
    rect_m(c, vv, 5.25, 0.15, 5.95, 0.2, fill=NEGRO, stroke=None)
    # succión con pichancha
    linea_m(c, vv, [(7.6, CIS_FONDO - 0.15), (7.6, 0.4), (8.5, 0.4)], 0.7, AZUL)
    rect_m(c, vv, 7.5, CIS_FONDO - 0.22, 7.7, CIS_FONDO - 0.05, fill=AZUL, stroke=None)
    texto(c, *vv.p(7.45, -1.2), 'Succión Ø 50', 1.6, 'Helvetica-Bold', 'r', AZUL)
    # llenado y flotador
    linea_m(c, vv, [(8.5, -0.25), (7.0, -0.25), (7.0, -0.45)], 0.5, VERDE)
    px, py = vv.p(6.7, -0.55)
    c.saveState(); lw(c, 0.2); c.setStrokeColor(VERDE); c.circle(px, py, 1.4); c.restoreState()
    linea_m(c, vv, [(7.0, -0.45), (6.75, -0.55)], 0.2, VERDE)
    texto(c, *vv.p(6.3, -0.15), 'Válv. flotador Ø 19', 1.6, al='r', col=VERDE)
    # electroniveles
    linea_m(c, vv, [(6.0, 0.0), (6.0, CIS_FONDO + 0.2)], 0.15, GRIS)
    for zz in (CIS_AGUA - 0.1, CIS_FONDO + 0.2):
        px, py = vv.p(6.0, zz)
        c.saveState(); lw(c, 0.2); c.circle(px, py, 0.8); c.restoreState()
    texto(c, *vv.p(5.9, CIS_FONDO + 0.15), 'Paro bajo nivel', 1.5, al='r')
    # ventilación
    linea_m(c, vv, [(X0 + 0.25, 0.15), (X0 + 0.25, 0.8), (X0 + 0.45, 0.8)], 0.3, GRIS)
    texto(c, *vv.p(X0 + 0.5, 0.75), 'Tubo ventilación Ø 50 c/ malla', 1.5)
    # cotas
    cota_v(c, vv, CIS_FONDO, CIS_AGUA, X1 + 0.2, 5, '%.2f útil' % (CIS_AGUA - CIS_FONDO))
    cota_v(c, vv, CIS_AGUA, 0.0, X1 + 0.2, 5, '0.40')
    cota_v(c, vv, CIS_FONDO, 0.0, X1 + 0.2, 11)
    cota_h(c, vv, X0, X1, CIS_FONDO - 0.2, -5)
    linea_m(c, vv, [(X0 - 0.6, 0.0), (X0 - 0.2, 0.0)], 0.3)
    linea_m(c, vv, [(X1 + 0.2, 0.0), (X1 + 0.6, 0.0)], 0.3)
    for z, s in ((0.15, '+0.15 Tapa'), (0.0, '±0.00 N.T.N.'), (CIS_AGUA, '%.2f N.A.M.' % CIS_AGUA),
                 (CIS_FONDO, '%.2f Fondo' % CIS_FONDO)):
        px, py = vv.p(X0 - 0.25, z)
        nivel_marca(c, px - 1, py, s, 1.6, izq=True)
    titulo_dibujo(c, 345, 112, "DETALLE CISTERNA · CORTE B-B'", 'Esc. 1:35')
    parrafo(c, 345, 100, [
        'Muros y losa de fondo de concreto f\'c = 250 kg/cm²',
        'con impermeabilizante integral; aplanado pulido',
        'interior; chaflanes 10 x 10 cm en esquinas;',
        'fondo con pendiente 1 % hacia el cárcamo.',
        'Tapa 15 cm sobre N.T.N. para evitar escurrimientos.',
    ], 1.9)


# ----------------------------------------------------------------------
#  LÁMINA IH-04  MEMORIA DE CÁLCULO Y REVISIÓN
# ----------------------------------------------------------------------
def tabla(c, x, y, cols, filas, t=1.95, h=3.05, enc=True):
    """cols: lista de (titulo, ancho, alineación)."""
    xx = x
    c.saveState(); lw(c, 0.1); c.setStrokeColor(GRIS)
    ancho = sum(w for _, w, _ in cols)
    c.restoreState()
    if enc:
        c.saveState(); c.setFillColor(GRIS_MC); c.rect(x, y - 0.9, ancho, h, fill=1, stroke=0); c.restoreState()
        for (tit, w, al) in cols:
            texto(c, xx + (w / 2 if al == 'c' else (w - 0.8 if al == 'r' else 0.8)), y,
                  tit, t, 'Helvetica-Bold', al)
            xx += w
        y -= h
    for f in filas:
        xx = x
        bold = isinstance(f, tuple) and f and f[0] == '**'
        celdas = f[1:] if bold else f
        for (tit, w, al), s in zip(cols, celdas):
            texto(c, xx + (w / 2 if al == 'c' else (w - 0.8 if al == 'r' else 0.8)), y,
                  str(s), t, 'Helvetica-Bold' if bold else 'Helvetica', al)
            xx += w
        c.saveState(); lw(c, 0.06); c.setStrokeColor(GRIS_C)
        c.line(x, y - 0.95, x + ancho, y - 0.95); c.restoreState()
        y -= h
    return y


def nombre_tramo(p, h):
    def n(s):
        base = s.split('_')[0]
        return base
    return '%s-%s' % (n(p), n(h))


def lamina_IH04(c):
    marco(c, 'IH-04', ['Memoria de cálculo', 'hidráulico y revisión', 'del proyecto'], 'S/E', 6)
    texto(c, 24, 392, 'MEMORIA DE CÁLCULO — AGUA POTABLE', 4.6, 'Helvetica-Bold')
    c.saveState()
    c.translate(24, 384); c.scale(1.25, 1.25); c.translate(-24, -384)
    _ih04_cuerpo(c)
    c.restoreState()


def _ih04_cuerpo(c):
    # ---------- columna 1 ----------
    x = 24
    y = 382
    y = parrafo(c, x, y, [
        '**1. Criterios de diseño adoptados',
        '· Referencia: Reglamento de Construcciones CDMX y sus NTC (instalaciones',
        '  hidráulicas). Adecuar dotación y presiones al reglamento local.',
        '· Gastos de diseño: método de Hunter (W.C. de tanque), limitado a la suma',
        '  de gastos individuales en ramales cortos.',
        '· Pérdidas: Hazen-Williams, C = %d (cobre); accesorios +%d %% de longitud.' % (C_HW, round((F_ACCES - 1) * 100)),
        '· Velocidad máxima %.1f m/s (ruido y golpe de ariete).' % V_MAX,
        '· Presión mínima en la salida más desfavorable: %.1f kg/cm² (%.0f m.c.a.).' % (P_MIN / 10, P_MIN),
        '· Presión estática máxima en muebles: %.1f kg/cm².' % (P_MAX / 10),
        '',
        '**2. Dotación y volumen de cisterna',
    ], 2.05)
    filas = [
        ('Departamentos', '4 (1 por nivel)'),
        ('Ocupación por depto. (3 rec. x 2 + 1)', '%d hab' % OCUP_DEPTO),
        ('Población total', '%d hab' % (OCUP_DEPTO * 4)),
        ('Dotación', '%d L/hab/día' % DOTACION),
        ('Consumo diario', '%s L/día' % format(CONSUMO, ',')),
        ('Días de almacenamiento (1 + 2 de reserva)', '%d' % DIAS),
        ('Volumen requerido', '%.2f m³' % V_CIS_REQ),
        ('Cisterna: %.2f x %.2f x %.2f m útil' % (CIS_X1 - CIS_X0, CIS_Y1 - CIS_Y0, CIS_AGUA - CIS_FONDO),
         '%.2f m³  OK' % V_CIS_UTIL if V_CIS_UTIL >= V_CIS_REQ else '%.2f m³  NO' % V_CIS_UTIL),
        ('Bordo libre / altura interior', '0.40 m / %.2f m' % (0.0 - CIS_FONDO)),
        ('Toma domiciliaria (llenado en ~8 h: %.2f L/s)' % (CONSUMO / 8 / 3600), 'Ø 19 mm'),
    ]
    y = tabla(c, x, y - 1, [('Concepto', 78, 'l'), ('Valor', 38, 'r')], filas)
    y -= 4
    y = parrafo(c, x, y, ['**3. Unidades mueble por departamento'], 2.05)
    cuenta = {}
    for k, d in RED.n.items():
        if d['fix'] and k.endswith('_0'):
            cuenta[d['fix']] = cuenta.get(d['fix'], 0) + 1
    filas = []
    for f in ('WC', 'LAV', 'REG', 'FRE', 'LDR', 'LVD', 'CAL'):
        n = cuenta.get(f, 0)
        m = MUEBLES[f]
        filas.append((m[3], n, m[0], n * m[0], '%.2f' % m[1], '%.2f' % m[2]))
    filas.append(('**', 'Total por departamento', '', '', UM_DEPTO, '', ''))
    filas.append(('**', 'Total edificio (4 deptos.)', '', '', UM_TOTAL, '', ''))
    y = tabla(c, x, y - 1, [('Mueble', 48, 'l'), ('Cant.', 12, 'c'), ('UM', 11, 'c'),
                            ('UM tot.', 15, 'c'), ('q ind. L/s', 16, 'c'), ('Salida m', 14, 'c')], filas)
    y -= 2
    y = parrafo(c, x, y, [
        '2 baños completos (W.C., lavabo, regadera) + 1 medio baño (W.C., lavabo)',
        '= 2½ baños por departamento.  El calentador no suma UM (su demanda ya',
        'está en los muebles de agua caliente); su ramal se revisa con 0.27 L/s.',
    ], 1.9)
    y -= 3
    y = parrafo(c, x, y, ['**4. Equipo de bombeo (presión constante)'], 2.05)
    filas = [
        ('Gasto máximo probable (%d UM)' % UM_TOTAL, '%.2f L/s' % Q_TOTAL),
        ('Presión de consigna en descarga', '%.1f m.c.a.' % P_CONSIGNA),
        ('Nivel mín. de succión / eje de bomba', '%.2f / +0.30 m' % Z_SUCC_MIN),
        ('Pérdidas en succión y equipo', '0.80 m'),
        ('Carga dinámica total (CDT)', '%.1f m' % CDT),
        ('Potencia = 9.81·Q·CDT / %.2f' % ETA, '%.2f kW = %.2f HP' % (POT_KW, POT_HP)),
        ('Selección', '2 x %g HP (1 + 1 reserva)' % HP_COM),
        ('Tanque precargado (con variador)', '80 L'),
    ]
    y = tabla(c, x, y - 1, [('Concepto', 78, 'l'), ('Valor', 38, 'r')], filas)

    # ---------- columna 2: tabla de tramos ----------
    x = 152
    y = 382
    y = parrafo(c, x, y, ['**5. Cálculo por tramos (ruta crítica y depto. del Nivel 3)'], 2.05)
    filas = []
    orden = ['EQ', 'P1', 'P2', 'P3', 'P4', 'R0', 'R1', 'R2', 'R3']
    for a, b in zip(orden, orden[1:]):
        inf = RED.info[(a, b)]
        filas.append((nombre_tramo(a, b), inf['um'], '%.2f' % inf['q'],
                      '%d (%s)' % (inf['dn'][0], inf['dn'][1]), '%.2f' % inf['v'],
                      '%.2f' % inf['L'], '%.2f' % inf['hf'], '%.1f' % RED.n[b]['p']))
    # recorrido del depto N3 (todo el árbol en preorden)
    def pre(nom):
        for h in RED.hijos[nom]:
            if not h.endswith('_3'):
                continue
            inf = RED.info[(nom, h)]
            if RED.n[h]['fix']:
                et = '%s→%s' % (nom.split('_')[0], ABREV[RED.n[h]['fix']])
            else:
                et = nombre_tramo(nom, h)
            filas.append((et.replace('→', '-'), inf['um'], '%.2f' % inf['q'],
                          '%d (%s)' % (inf['dn'][0], inf['dn'][1]),
                          '%.2f' % inf['v'], '%.2f' % inf['L'], '%.2f' % inf['hf'],
                          '%.1f' % RED.n[h]['p']))
            pre(h)
    pre('R3')
    y = tabla(c, x, y - 1, [('Tramo', 22, 'l'), ('UM', 10, 'c'), ('Q L/s', 13, 'c'),
                            ('Ø mm (pulg)', 24, 'c'), ('v m/s', 12, 'c'), ('L m', 11, 'c'),
                            ('hf m', 11, 'c'), ('P m.c.a.', 15, 'c')], filas, t=1.8, h=2.78)
    y = parrafo(c, x, y - 1.5, [
        'hf incluye +25 %% por accesorios; en el tramo R3-A además %.1f m de válvula,' % H_MEDIDOR,
        'medidor y check. P = presión en el nodo final del tramo (m.c.a.).',
        'Tramos sin muebles (eliminador de aire) no se listan.',
    ], 1.8)

    # ---------- columna 3: presiones y revisión ----------
    x = 282
    y = 382
    y = parrafo(c, x, y, ['**6. Presiones en el mueble más desfavorable por nivel'], 2.05)
    filas = []
    for lev in range(4):
        ks = [k for k in FIXT if k.endswith('_%d' % lev)]
        kmin = min(ks, key=presion_salida)
        pmin = presion_salida(kmin)
        pest = max(P_CONSIGNA + 0.30 - RED.ztrue(k) for k in ks)
        filas.append((NIVELES[lev], '%s (%s)' % (MUEBLES[RED.n[kmin]['fix']][3].split(' (')[0],
                                                 kmin.split('_')[0][-2:].upper()),
                      '%.1f' % pmin, '%.1f' % pest,
                      'OK' if pmin >= P_MIN and pest <= P_MAX else 'NO'))
    y = tabla(c, x, y - 1, [('Nivel', 18, 'l'), ('Mueble crítico', 40, 'l'), ('P din. m', 15, 'c'),
                            ('P est. máx', 16, 'c'), ('', 8, 'c')], filas)
    y = parrafo(c, x, y - 1, [
        'Regadera evaluada en la cebolleta (+1.90 m). P din. = con gasto máximo;',
        'P est. máx = sin flujo, en el mueble más bajo del nivel.',
    ], 1.8)
    y -= 4
    y = parrafo(c, x, y, ['**7. Revisión del proyecto (lo que se pidió vs. lo entregado)'], 2.05)
    chk = [
        ('Edificio de mínimo 4 pisos', 'PB + 3 niveles = 4 pisos', 'CUMPLE'),
        ('Mínimo 2.5 baños', '2 completos + 1 medio por depto.', 'CUMPLE'),
        ('Isométrico de agua potable', 'IH-02 general y IH-03 depto.', 'CUMPLE'),
        ('Cisterna en el isométrico', 'IH-02 + detalles IH-03', 'CUMPLE'),
        ('Plantas normales', 'A-01 (PB, tipo, azotea), IH-01', 'CUMPLE'),
        ('Elevación', 'A-02 fachada + corte A-A\'', 'CUMPLE'),
        ('Volumen de cisterna', '%.1f >= %.1f m³' % (V_CIS_UTIL, V_CIS_REQ),
         'CUMPLE' if V_CIS_UTIL >= V_CIS_REQ else 'NO'),
        ('Velocidades', 'máx. %.2f m/s <= %.1f' % (max(i['v'] for i in RED.info.values()), V_MAX),
         'CUMPLE' if max(i['v'] for i in RED.info.values()) <= V_MAX else 'NO'),
        ('Presión mín. (salida crítica)', '%.1f >= %.1f m.c.a.' % (P_PEOR, P_MIN),
         'CUMPLE' if P_PEOR >= P_MIN else 'NO'),
        ('Presión estática máx.', '%.1f <= %.1f m.c.a.' % (P_EST_MAX, P_MAX),
         'CUMPLE' if P_EST_MAX <= P_MAX else 'NO'),
    ]
    y = tabla(c, x, y - 1, [('Requisito', 42, 'l'), ('Resultado', 46, 'l'), ('', 15, 'c')], chk)
    y -= 4
    y = parrafo(c, x, y, [
        '**8. Observaciones de la revisión (correcciones al esquema típico)',
        '· Se descartó el esquema "cisterna + tinaco en azotea por gravedad": con el',
        '  tinaco a +%.1f m, la regadera del Nivel 3 tendría sólo %.1f m.c.a.' % (Z_TINACO, P_TINACO_N3),
        '  (%.2f kg/cm²), muy por debajo del mínimo de %.1f kg/cm². Se cambió a' % (P_TINACO_N3 / 10, P_MIN / 10),
        '  equipo de presión constante desde la cisterna.',
        '· Al no haber tinacos, toda la reserva queda en la cisterna: se diseñó',
        '  para %d días de consumo (%.1f m³) en lugar de 2/3 del total.' % (DIAS, V_CIS_REQ),
        '· Con hidroneumático de arranque/paro 35-55 psi la regadera del N3 bajaría',
        '  a %.1f m.c.a. (< %.0f) y la P.B. subiría a 3.9 kg/cm²; por eso se usa variador' % (
            P_PEOR - (P_CONSIGNA - 24.6), P_MIN),
        '  a presión constante %.1f kg/cm² (sin válvulas reductoras).' % (P_CONSIGNA / 10),
        '· Diámetros elegidos por velocidad <= %.1f m/s: montante %d-%d-%d mm,' % (
            V_MAX, RED.info[('P4', 'R0')]['dn'][0], RED.info[('R1', 'R2')]['dn'][0],
            RED.info[('R2', 'R3')]['dn'][0]),
        '  entrada a depto. %d mm, ramales %d-%d mm, salidas 13 mm.' % (
            RED.info[('R3', 'A_3')]['dn'][0], RED.info[('A_3', 'B_3')]['dn'][0],
            RED.info[('B_3', 'D_3')]['dn'][0] if RED.info[('B_3', 'D_3')]['dn'][0] < RED.info[('A_3', 'B_3')]['dn'][0] else 19),
        '· Cisterna a 1.80 m de colindancia y > 3 m de albañales; tapa elevada.',
        '· Recámara 3 y baño principal ventilan al cubo de luz (2.00 x 2.00 m);',
        '  medio baño con extractor mecánico.',
        '· Para 4 niveles (h < 13 m) no se proyecta elevador; verificar con el',
        '  reglamento local si se exige.',
        '',
        '**Este es un proyecto tipo de referencia. Para construir, debe',
        '**ajustarse al terreno, a la normativa local y firmarse por un D.R.O.',
    ], 1.95)


# ----------------------------------------------------------------------
def main():
    c = canvas.Canvas(SALIDA, pagesize=(PW * mm, PH * mm))
    c.setTitle('Edificio 4 niveles - Planos e isométrico de agua potable')
    c.setAuthor('Proyecto tipo')
    for f in (lamina_A01, lamina_A02, lamina_IH01, lamina_IH02, lamina_IH03, lamina_IH04):
        c.saveState()
        c.scale(mm, mm)
        f(c)
        c.restoreState()
        c.showPage()
    c.save()
    print('PDF:', SALIDA)
    print('UM depto %d, total %d, Q %.2f L/s' % (UM_DEPTO, UM_TOTAL, Q_TOTAL))
    print('Cisterna req %.2f, util %.2f' % (V_CIS_REQ, V_CIS_UTIL))
    print('Peor salida %s P=%.2f ; P est max %.2f' % (PEOR, P_PEOR, P_EST_MAX))
    print('CDT %.1f  Pot %.2f HP -> %g HP' % (CDT, POT_HP, HP_COM))
    print('Tinaco N3: %.2f' % P_TINACO_N3)
    for (p, h), i in RED.info.items():
        if h.endswith('_3') or i.get('tipo'):
            print('%-8s %-8s UM%3d Q%.2f D%d v%.2f L%.2f hf%.2f P%.1f' % (
                p, h, i['um'], i['q'], i['dn'][0], i['v'], i['L'], i['hf'], RED.n[h]['p']))


if __name__ == '__main__':
    main()
