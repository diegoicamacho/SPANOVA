# -*- coding: utf-8 -*-
"""
Lienzo compatible con la parte de reportlab.Canvas que usan los planos,
pero que escribe entidades DXF (ezdxf). Así el PDF y el DXF salen del
mismo código de dibujo.

Unidades: milímetros de pliego (1:100 => 1 m = 10 mm).
"""
import math

import ezdxf
from ezdxf.enums import TextEntityAlignment
from reportlab.pdfbase.pdfmetrics import stringWidth

LW_VALIDOS = [0, 5, 9, 13, 15, 18, 20, 25, 30, 35, 40, 50, 53, 60, 70, 80, 90, 100, 106, 120,
              140, 158, 200, 211]


def _rgb(col):
    if col is None:
        return None
    return (round(col.red, 3), round(col.green, 3), round(col.blue, 3))


# color reportlab -> (capa, ACI, true color o None)
def _clasificar(rgb):
    if rgb is None:
        return None
    r, g, b = rgb
    if r > 0.97 and g > 0.97 and b > 0.97:
        return None                                    # blanco: se omite (sólo enmascaraba)
    if b > 0.6 and r < 0.2:
        return ('AGUA_FRIA', 140, None)
    if r > 0.7 and g < 0.3:
        return ('AGUA_CALIENTE', 1, None)
    if g > 0.4 and r < 0.2 and b < 0.3:
        return ('TOMA_MUNICIPAL', 3, None)
    if b > 0.95 and r > 0.7:
        return ('RELLENO_AGUA', 254, (204, 229, 255))  # azul claro
    if r < 0.05 and g < 0.05 and b < 0.05:
        return ('LINEAS', 7, None)                     # 7 = negro/blanco según el fondo
    if r < 0.6:
        return ('GRIS', 8, None)
    if r < 0.8:
        return ('GRIS_CLARO', 9, None)
    return ('RELLENO_GRIS', 254, (225, 225, 225))


def _mul(m, n):
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a * A + c * B, b * A + d * B, a * C + c * D, b * C + d * D,
            a * E + c * F + e, b * E + d * F + f)


class _Path:
    def __init__(self):
        self.subs = []

    def moveTo(self, x, y):
        self.subs.append([[(x, y)], False])

    def lineTo(self, x, y):
        self.subs[-1][0].append((x, y))

    def close(self):
        self.subs[-1][1] = True


class DXFCanvas:
    def __init__(self):
        self.doc = ezdxf.new('R2018', setup=True)
        self.doc.header['$INSUNITS'] = 4          # mm
        self.doc.header['$LWDISPLAY'] = 1
        self.msp = self.doc.modelspace()
        for nom, aci in (('LINEAS', 7), ('GRIS', 8), ('GRIS_CLARO', 9), ('AGUA_FRIA', 140),
                         ('AGUA_CALIENTE', 1), ('TOMA_MUNICIPAL', 3), ('RELLENO_AGUA', 254),
                         ('RELLENO_GRIS', 254), ('TEXTO', 7)):
            if nom not in self.doc.layers:
                self.doc.layers.add(nom, color=aci)
        self.doc.styles.add('PLANO', font='arial.ttf')
        self.doc.styles.add('PLANO_B', font='arialbd.ttf')
        self.m = (1, 0, 0, 1, 0, 0)
        self.st = dict(lw=0.2, stroke=(0, 0, 0), fill=(0, 0, 0), dash=None, font=('Helvetica', 2.0))
        self.pila = []
        self._lt = {}

    # ------------------------------------------------------------ estado
    def saveState(self):
        self.pila.append((self.m, dict(self.st)))

    def restoreState(self):
        self.m, self.st = self.pila.pop()

    def translate(self, x, y):
        self.m = _mul(self.m, (1, 0, 0, 1, x, y))

    def rotate(self, ang):
        a = math.radians(ang)
        self.m = _mul(self.m, (math.cos(a), math.sin(a), -math.sin(a), math.cos(a), 0, 0))

    def scale(self, sx, sy):
        self.m = _mul(self.m, (sx, 0, 0, sy, 0, 0))

    def setLineWidth(self, w):
        self.st['lw'] = w

    def setStrokeColor(self, c):
        self.st['stroke'] = _rgb(c)

    def setFillColor(self, c):
        self.st['fill'] = _rgb(c)

    def setDash(self, arr=None, phase=0):
        if isinstance(arr, (int, float)):
            arr = [arr, phase]
        self.st['dash'] = tuple(arr) if arr else None

    def setFont(self, nombre, t):
        self.st['font'] = (nombre, t)

    def stringWidth(self, s, nombre, t):
        return stringWidth(s, nombre, t)

    def setTitle(self, *a):
        pass

    def setAuthor(self, *a):
        pass

    # ------------------------------------------------------------ utilidades
    def _P(self, x, y):
        a, b, c, d, e, f = self.m
        return (a * x + c * y + e, b * x + d * y + f)

    def _escala(self):
        a, b, c, d, e, f = self.m
        return math.sqrt(abs(a * d - b * c))

    def _attrs(self, col, con_lt=True):
        k = _clasificar(col)
        if k is None:
            return None
        capa, aci, tc = k
        at = {'layer': capa, 'color': 256}
        if tc:
            at['true_color'] = ezdxf.colors.rgb2int(tc)
        w = self.st['lw'] * self._escala() * 100
        at['lineweight'] = min(LW_VALIDOS, key=lambda v: abs(v - w))
        if con_lt and self.st['dash']:
            at['linetype'] = self._linetype(self.st['dash'])
        return at

    def _linetype(self, dash):
        k = self._escala()
        pat = [round(v * k, 3) for v in dash]
        if len(pat) % 2:
            pat = pat * 2
        nom = 'PLANO_' + '_'.join(('%g' % v).replace('.', 'p') for v in pat)
        if nom not in self._lt:
            elems = []
            for i, v in enumerate(pat):
                elems.append(v if i % 2 == 0 else -v)
            self.doc.linetypes.add(nom, pattern=[sum(pat)] + elems, description=nom)
            self._lt[nom] = True
        return nom

    def _hatch(self, at):
        h = self.msp.add_hatch(dxfattribs={'layer': at['layer']})
        if 'true_color' in at:
            h.set_solid_fill(rgb=ezdxf.colors.int2rgb(at['true_color']))
        else:
            h.set_solid_fill(color=256)
        return h

    def _poli(self, pts, cerrada, stroke=True, fill=False):
        P = [self._P(*p) for p in pts]
        if fill:
            at = self._attrs(self.st['fill'], False)
            if at:
                self._hatch(at).paths.add_polyline_path(P, is_closed=True)
        if stroke:
            at = self._attrs(self.st['stroke'])
            if at:
                self.msp.add_lwpolyline(P, close=cerrada, dxfattribs=at)

    # ------------------------------------------------------------ primitivas
    def line(self, x1, y1, x2, y2):
        at = self._attrs(self.st['stroke'])
        if at:
            self.msp.add_line(self._P(x1, y1), self._P(x2, y2), dxfattribs=at)

    def rect(self, x, y, w, h, stroke=1, fill=0):
        self._poli([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], True, bool(stroke), bool(fill))

    def roundRect(self, x, y, w, h, r, stroke=1, fill=0):
        r = min(r, w / 2, h / 2)
        pts = []
        for (cx, cy, a0) in ((x + w - r, y + r, -90), (x + w - r, y + h - r, 0),
                             (x + r, y + h - r, 90), (x + r, y + r, 180)):
            for i in range(7):
                a = math.radians(a0 + i * 15)
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        self._poli(pts, True, bool(stroke), bool(fill))

    def circle(self, x, y, r, stroke=1, fill=0):
        cx, cy = self._P(x, y)
        R = r * self._escala()
        if fill:
            at = self._attrs(self.st['fill'], False)
            if at:
                ep = self._hatch(at).paths.add_edge_path()
                ep.add_arc((cx, cy), R, 0, 360)
        if stroke:
            at = self._attrs(self.st['stroke'])
            if at:
                self.msp.add_circle((cx, cy), R, dxfattribs=at)

    def ellipse(self, x1, y1, x2, y2, stroke=1, fill=0):
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        rx, ry = abs(x2 - x1) / 2, abs(y2 - y1) / 2
        n = 36
        pts = [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n))
               for i in range(n)]
        self._poli(pts, True, bool(stroke), bool(fill))

    def arc(self, x1, y1, x2, y2, start=0, extent=90):
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        rx, ry = abs(x2 - x1) / 2, abs(y2 - y1) / 2
        n = max(6, int(abs(extent) / 6))
        pts = []
        for i in range(n + 1):
            a = math.radians(start + extent * i / n)
            pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
        self._poli(pts, False)

    def beginPath(self):
        return _Path()

    def drawPath(self, p, stroke=1, fill=0, **kw):
        for pts, cerr in p.subs:
            if len(pts) > 1:
                self._poli(pts, cerr or bool(fill), bool(stroke), bool(fill))

    # ------------------------------------------------------------ texto
    def _texto(self, x, y, s, al):
        if not s:
            return
        nombre, t = self.st['font']
        col = self.st['fill']
        k = _clasificar(col) or ('TEXTO', 7, None)
        capa = 'TEXTO' if k[0] in ('LINEAS',) else k[0]
        a, b, c, d, e, f = self.m
        rot = math.degrees(math.atan2(b, a))
        h = t * self._escala() * 0.72
        at = {'layer': capa, 'color': 256, 'height': h, 'rotation': rot,
              'style': 'PLANO_B' if 'Bold' in nombre else 'PLANO'}
        txt = self.msp.add_text(s, dxfattribs=at)
        p = self._P(x, y)
        txt.set_placement(p, align={'l': TextEntityAlignment.LEFT,
                                    'c': TextEntityAlignment.BOTTOM_CENTER,
                                    'r': TextEntityAlignment.BOTTOM_RIGHT}[al])

    def drawString(self, x, y, s):
        self._texto(x, y, s, 'l')

    def drawCentredString(self, x, y, s):
        self._texto(x, y, s, 'c')

    def drawRightString(self, x, y, s):
        self._texto(x, y, s, 'r')

    def save(self, ruta):
        self.doc.saveas(ruta)
