"""MSP-EXP430G2ET LaunchPad 3D gorunumu: saf Tkinter yazilim renderer'i (harici bagimlilik yok).

Geometri TI'nin kart tasarim dosyalarindan uretildi (board_g2et.py): parca yerlesimleri, kart kenari,
silkscreen ve padler gercek olculerdedir (mm). Simulatorun pin durumlari kart uzerinde gosterilir:
LED'ler (D1 yesil=P1.0, D2 kirmizi=P1.6, D3 RGB=P2.1/P2.3/P2.5), header pinleri ve DIP bacaklari
(lojik seviye), J101 TXD/RXD jumper'lari (UART trafigi). S1 (P1.3) ve S2 (RESET) tiklanabilir.

Bu dosyanin ust kismi (Scene, Camera, pin_states) Tk gerektirmez; test edilebilir.
"""
import math
import time

from . import board_g2et as B

# ---------------------------------------------------------------- renkler
BG = '#23272e'
SHADOW = '#1a1d22'
PCB = '#b0151d'            # TI kirmizi lehim maskesi
PCB_EDGE = '#7d1a1e'
SILK = '#f4f4f0'
GOLD = '#d8b24e'           # ENIG pad / header pinleri
TIN = '#c9c9c9'
BLACK = '#18181a'
LIGHT = (-0.35, -0.5, 1.0)

LED_ON = {'green': '#3dff6e', 'red': '#ff2a1a', 'yellow': '#ffd21a'}
LED_OFF = {'green': '#c9dcc4', 'red': '#e2bcb6', 'yellow': '#e6dfb4'}
PIN_COL = {'out1': '#ff6d00', 'out0': '#2f6bff', 'in1': '#fff08a', 'in0': '#8f8f8f'}
FLASH = {'TXD': '#4fc3f7', 'RXD': '#7CFC7C'}


def _rgb(c):
    return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)


def _hex(r, g, b):
    return '#%02x%02x%02x' % (max(0, min(255, int(r))), max(0, min(255, int(g))), max(0, min(255, int(b))))


def shade(c, k):
    r, g, b = _rgb(c)
    return _hex(r * k, g * k, b * k)


def mix(a, b, t):
    (r1, g1, b1), (r2, g2, b2) = _rgb(a), _rgb(b)
    return _hex(r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t)


def add(a, b, t):
    """Isik gibi toplamsal karisim: a + b*t."""
    (r1, g1, b1), (r2, g2, b2) = _rgb(a), _rgb(b)
    return _hex(r1 + r2 * t, g1 + g2 * t, b1 + b2 * t)


def _norm(v):
    n = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2) or 1.0
    return v[0] / n, v[1] / n, v[2] / n


_L = _norm(LIGHT)


def light_factor(n):
    return 0.52 + 0.48 * max(0.0, n[0] * _L[0] + n[1] * _L[1] + n[2] * _L[2])


# ---------------------------------------------------------------- pin haritalari
# LaunchPad standardi (SLAU772 Sekil 10 / sematik): header pin no -> sinyal
J1_MAP = {1: '3V3', 2: ('P1', 0), 3: ('P1', 1), 4: ('P1', 2), 5: ('P1', 3), 6: ('P1', 4), 7: ('P1', 5),
          8: ('P2', 0), 9: ('P2', 1), 10: ('P2', 2)}
J2_MAP = {20: 'GND', 19: ('P2', 6), 18: ('P2', 7), 17: 'TEST', 16: 'RST', 15: ('P1', 7), 14: ('P1', 6),
          13: ('P2', 5), 12: ('P2', 4), 11: ('P2', 3)}
J3_MAP = {21: '5V', 22: 'GND'}
# MSP430G2553 PDIP-20 (SLAU772 Sekil 4)
DIP_MAP = {1: 'DVCC', 2: ('P1', 0), 3: ('P1', 1), 4: ('P1', 2), 5: ('P1', 3), 6: ('P1', 4), 7: ('P1', 5),
           8: ('P2', 0), 9: ('P2', 1), 10: ('P2', 2), 11: ('P2', 3), 12: ('P2', 4), 13: ('P2', 5),
           14: ('P1', 6), 15: ('P1', 7), 16: 'RST', 17: 'TEST', 18: ('P2', 7), 19: ('P2', 6), 20: 'DVSS'}
# LED -> (renk, surucu pin(ler), jumper)
LEDS = {'D1': ('green', ('P1', 0), 'J6'), 'D2': ('red', ('P1', 6), 'J7'),
        'D3': ('rgb', (('P2', 1), ('P2', 3), ('P2', 5)), 'J8'),
        'D100': ('red', None, 'eZ-FET Mode'), 'D101': ('green', None, 'eZ-FET Power'),
        'D102': ('yellow', None, 'eZ-FET LDO')}


def sig_name(s):
    return f'{s[0]}.{s[1]}' if isinstance(s, tuple) else s


def pin_states(cpu):
    """{('P1', bit): (level, is_output)} -- GUI'deki I/O panelinin kullandigi mantikla ayni."""
    out = {}
    for name, port in (('P1', cpu.p1), ('P2', cpu.p2)):
        lv, dr = port.pins(), port.rg[2]
        for b in range(8):
            out[(name, b)] = (lv >> b & 1, dr >> b & 1)
    return out


def pin_class(state):
    lvl, out = state
    return ('out' if out else 'in') + str(lvl)


def led_levels(pins):
    """LED parlakliklari 0..1 (D3 icin (r, g, b))."""
    def br(sig):
        lvl, out = pins[sig]
        return 1.0 if lvl and out else 0.0
    return {'D1': br(('P1', 0)), 'D2': br(('P1', 6)),
            'D3': tuple(br(s) for s in LEDS['D3'][1])}


# ---------------------------------------------------------------- sahne (geometri)
class Box:
    """Konveks govde: yuzler (vertex indeksleri, normal, duzlem d, taban renk, isik carpani)."""
    __slots__ = ('faces', 'center', 'order', 'only', 'tag')

    def __init__(self, faces, center, order, only, tag):
        self.faces, self.center, self.order, self.only, self.tag = faces, center, order, only, tag


class Group:
    __slots__ = ('name', 'side', 'boxes', 'lo', 'hi', 'label')

    def __init__(self, name, side):
        self.name, self.side, self.boxes = name, side, []
        self.lo, self.hi = [1e9] * 3, [-1e9] * 3
        self.label = None


class Scene:
    """Kartin tum 3D geometrisi. Koordinatlar mm; z=0 kartin ust yuzeyi, z=-T alt yuzey."""

    def __init__(self):
        self.V = []                     # [(x, y, z)]
        self.groups = []
        self.decals = {'T': [], 'B': []}   # (kind, idx, color, width, role, hq)
        self.board_sides = []           # yuzler
        self.board_top = self.board_bot = None
        self.T = B.T
        self._build()

    # --- ilkel yapicilar ---
    def _vert(self, x, y, z):
        self.V.append((x, y, z))
        return len(self.V) - 1

    def box(self, g, cx, cy, rot, lx, ly, sx, sy, z0, z1, color, role=None, order=0, only=None, tag=None):
        """Parca merkezi (cx, cy) + yerel ofset (lx, ly), yerel boyut sx*sy, z0..z1, rot derece."""
        c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        pts = []
        for ux, uy in ((-sx / 2, -sy / 2), (sx / 2, -sy / 2), (sx / 2, sy / 2), (-sx / 2, sy / 2)):
            x, y = lx + ux, ly + uy
            pts.append((cx + x * c - y * s, cy + x * s + y * c))
        base = len(self.V)
        for z in (z0, z1):
            for x, y in pts:
                self.V.append((x, y, z))
        ax, ay = c, s            # yerel +x yonu
        bx, by = -s, c           # yerel +y yonu
        quads = (((0, 3, 2, 1), (0, 0, -1)), ((4, 5, 6, 7), (0, 0, 1)),
                 ((0, 1, 5, 4), (-bx, -by, 0)), ((1, 2, 6, 5), (ax, ay, 0)),
                 ((2, 3, 7, 6), (bx, by, 0)), ((3, 0, 4, 7), (-ax, -ay, 0)))
        return self._add(g, base, quads, color, role, order, only, tag)

    def prism(self, g, cx, cy, r, z0, z1, n, color, role=None, order=0, only=None, tag=None, a0=0.0):
        base = len(self.V)
        ring = [(cx + r * math.cos(a0 + 2 * math.pi * k / n), cy + r * math.sin(a0 + 2 * math.pi * k / n))
                for k in range(n)]
        for z in (z0, z1):
            for x, y in ring:
                self.V.append((x, y, z))
        quads = [(tuple(range(n - 1, -1, -1)), (0, 0, -1)), (tuple(range(n, 2 * n)), (0, 0, 1))]
        for k in range(n):
            k2 = (k + 1) % n
            am = a0 + 2 * math.pi * (k + 0.5) / n
            quads.append(((k, k2, n + k2, n + k), (math.cos(am), math.sin(am), 0)))
        return self._add(g, base, quads, color, role, order, only, tag)

    def _add(self, g, base, quads, color, role, order, only, tag):
        faces = []
        for idx, n in quads:
            idx = tuple(base + i for i in idx)
            p = self.V[idx[0]]
            k = light_factor(n)
            faces.append((idx, n, n[0] * p[0] + n[1] * p[1] + n[2] * p[2], color, k, shade(color, k), role))
        xs = [self.V[i] for i in range(base, len(self.V))]
        ctr = tuple(sum(v[a] for v in xs) / len(xs) for a in range(3))
        for v in xs:
            for a in range(3):
                g.lo[a] = min(g.lo[a], v[a])
                g.hi[a] = max(g.hi[a], v[a])
        b = Box(faces, ctr, order, only, tag)
        g.boxes.append(b)
        return b

    def group(self, name, side='T'):
        g = Group(name, side)
        self.groups.append(g)
        return g

    def decal(self, side, kind, flat, color, width=0.0, role=None, hq=False, z=None):
        if len(flat) < (6 if kind == 'poly' else 4):
            return
        if z is None:
            z = 0.004 if side == 'T' else -self.T - 0.004
        idx = [self._vert(flat[i], flat[i + 1], z) for i in range(0, len(flat), 2)]
        self.decals[side].append((kind, idx, color, width, role, hq))

    def disc(self, side, x, y, r, color, role=None, n=16, hq=False, z=None):
        flat = []
        for k in range(n):
            a = 2 * math.pi * k / n
            flat += [x + r * math.cos(a), y + r * math.sin(a)]
        self.decal(side, 'poly', flat, color, role=role, hq=hq, z=z)

    # --- kart ---
    def _build_board(self):
        ol = B.OUTLINE
        area = sum(ol[i][0] * ol[(i + 1) % len(ol)][1] - ol[(i + 1) % len(ol)][0] * ol[i][1] for i in range(len(ol)))
        ccw = area > 0
        top = [self._vert(x, y, 0.0) for x, y in ol]
        bot = [self._vert(x, y, -self.T) for x, y in ol]
        n = len(ol)
        for i in range(n):
            j = (i + 1) % n
            dx, dy = ol[j][0] - ol[i][0], ol[j][1] - ol[i][1]
            nn = _norm((dy, -dx, 0) if ccw else (-dy, dx, 0))
            idx = (top[i], top[j], bot[j], bot[i])
            p = self.V[top[i]]
            k = light_factor(nn)
            self.board_sides.append((idx, nn, nn[0] * p[0] + nn[1] * p[1], PCB_EDGE, k, shade(PCB_EDGE, k), None))
        self.board_top = (top, shade(PCB, light_factor((0, 0, 1))))
        self.board_bot = (bot, shade(PCB, 0.55))
        self.shadow = [self._vert(x + 1.5, y - 2.0, -11.6) for x, y in ol]

    # --- parca kutuphanesi (yerel eksen: rot=0'da padler +-x yonunde) ---
    def _passive(self, g, ref, x, y, rot, L, W, H, kind):
        e = max(0.18, L * 0.2)
        ends = TIN
        body = {'R': '#1c1c1c', 'C': '#bfa070', 'L': '#3b3b3b'}.get(kind, '#bfa070')
        self.box(g, x, y, rot, -(L - e) / 2, 0, e, W, 0, H, ends)
        self.box(g, x, y, rot, (L - e) / 2, 0, e, W, 0, H, ends)
        self.box(g, x, y, rot, 0, 0, L - 2 * e, W * 0.98, 0, H * 0.98, body)

    def _tantalum(self, g, x, y, rot):
        self.box(g, x, y, rot, 0, 0, 2.4, 1.6, 0, 1.6, '#e8b51e')
        self.box(g, x, y, rot, -1.2, 0, 0.35, 1.2, 0, 0.9, TIN, order=-1)
        self.box(g, x, y, rot, 1.2, 0, 0.35, 1.2, 0, 0.9, TIN, order=-1)
        self.box(g, x, y, rot, -0.95, 0, 0.35, 1.6, 1.6, 1.62, '#9a6b0e', order=1)

    def _ic(self, g, x, y, rot, sx, sy, h, legs=(), color='#262626', dot=True):
        self.box(g, x, y, rot, 0, 0, sx, sy, 0.05, h, color)
        for lx, ly, lsx, lsy in legs:
            self.box(g, x, y, rot, lx, ly, lsx, lsy, 0, 0.18, TIN, order=-1)
        if dot and min(sx, sy) >= 1.9:
            self.box(g, x, y, rot, -sx / 2 + 0.6, sy / 2 - 0.6, 0.45, 0.45, h, h + 0.01, '#4a4a4a', order=1)

    def _led(self, g, ref, x, y, rot, rgb=False):
        if rgb:
            self.box(g, x, y, rot, 0, 0, 1.6, 1.5, 0, 0.25, '#efefea')
            self.box(g, x, y, rot, 0, 0, 1.25, 1.15, 0.25, 0.55, '#e8e8e8', role=('lens', ref), order=1, tag='h:' + ref)
        else:
            self.box(g, x, y, rot, 0, 0, 1.6, 0.8, 0, 0.35, '#efefea', tag='h:' + ref)
            self.box(g, x, y, rot, -0.68, 0, 0.24, 0.8, 0, 0.3, TIN, order=-1)
            self.box(g, x, y, rot, 0.68, 0, 0.24, 0.8, 0, 0.3, TIN, order=-1)
            self.box(g, x, y, rot, 0, 0, 1.15, 0.72, 0.35, 0.75, '#dddddd', role=('lens', ref), order=1, tag='h:' + ref)
        col = LEDS[ref][0]
        base = '#ffffff' if col == 'rgb' else LED_ON[col]
        self.disc('T', x, y, 3.6, add(PCB, base, 0.3), role=('spill', ref), n=18, z=0.008)
        self.disc('T', x, y, 1.9, add(PCB, base, 0.65), role=('spill', ref), n=14, z=0.009)

    def _male_header(self, g, x, y, rot, nx, ny, h, pin_col):
        p = 2.54
        self.box(g, x, y, rot, 0, 0, nx * p, ny * p, 0, 2.5, '#141414')
        for i in range(nx):
            for j in range(ny):
                lx, ly = (i - (nx - 1) / 2) * p, (j - (ny - 1) / 2) * p
                self.box(g, x, y, rot, lx, ly, 0.64, 0.64, 2.5, h, pin_col, order=1)

    def _shunt(self, g, x, y, rot, role=None, tag=None):
        self.box(g, x, y, rot, 0, 0, 5.0, 2.5, 2.5, 8.6, '#141416', role=role, order=2, tag=tag)
        self.box(g, x, y, rot, 0, 0, 3.4, 1.2, 8.6, 8.62, '#060606', order=3, tag=tag)

    def _stack_header(self, ref, x, y, pins):
        """BoosterPack: alt yuzde disi soket (SSQ), uste uzun kuyruklar = erkek pin."""
        n = len(pins)
        top = self.group(ref, 'T')
        for k, (num, sig) in enumerate(pins):
            py = y + ((n - 1) / 2 - k) * 2.54
            self.box(top, x, py, 0, 0, 0, 1.25, 1.25, 0, 0.35, '#d0d0d0')
            self.box(top, x, py, 0, 0, 0, 0.64, 0.64, 0.35, 6.0, GOLD, role=('pin', (ref, num)), order=1,
                     tag=f'h:pin:{ref}:{num}')
        bot = self.group(ref + '_bot', 'B')
        self.box(bot, x, y, 0, 0, 0, 2.54, 2.54 * n, -self.T - 8.5, -self.T, '#151515')
        for k in range(n):
            py = y + ((n - 1) / 2 - k) * 2.54
            self.box(bot, x, py, 0, 0, 0, 0.9, 0.9, -self.T - 8.55, -self.T - 8.5, '#000000', order=1)

    def _dip(self, x, y):
        """XU1 Mill-Max soket + MSP430G2553IN20 (pin 1 sol ust)."""
        g = self.group('XU1', 'T')
        self.box(g, x, y, 0, -3.81, 0, 2.3, 26.6, 0, 3.0, '#161616')
        self.box(g, x, y, 0, 3.81, 0, 2.3, 26.6, 0, 3.0, '#161616')
        self.box(g, x, y, 0, 0, 12.55, 5.3, 1.5, 0, 3.0, '#161616')
        self.box(g, x, y, 0, 0, -12.55, 5.3, 1.5, 0, 3.0, '#161616')
        for side in (-1, 1):
            for k in range(10):
                py = 11.43 - k * 2.54
                self.prism(g, x + side * 3.81, y + py, 0.75, 3.0, 3.03, 8, GOLD, order=1, a0=math.pi / 8)
        self.box(g, x, y, 0, 0, 0, 6.35, 26.0, 3.35, 6.6, '#1c1c1e', order=2, tag='h:XU1')
        for num in range(1, 21):
            side, k = (-1, num - 1) if num <= 10 else (1, 20 - num)
            py = 11.43 - k * 2.54
            role, tag = ('pin', ('XU1', num)), f'h:pin:XU1:{num}'
            self.box(g, x, y, 0, side * 3.6, py, 0.85, 1.5, 4.55, 4.85, TIN, role=role, order=3, tag=tag)
            self.box(g, x, y, 0, side * 3.86, py, 0.26, 0.5, 3.0, 4.85, TIN, role=role, order=3, tag=tag)
        self.box(g, x, y, 0, 0, 12.1, 1.6, 0.9, 6.6, 6.61, '#0c0c0c', order=4)        # centik
        self.prism(g, x - 2.0, y + 10.9, 0.45, 6.6, 6.61, 10, '#0c0c0c', order=4)    # pin-1 noktasi
        g.label = ((x, y, 6.62), (x, y - 1, 6.62), 'MSP430G2553IN20', 1.25)

    def _switch(self, ref, x, y, rot):
        """1188E yandan basmali tact switch; buton kart kenarina dogru (-x yerel)."""
        g = self.group(ref, 'T')
        t = 'h:' + ref
        self.box(g, x, y, rot, 0.0, 0, 3.0, 6.0, 0, 1.6, '#202020', tag=t)
        self.box(g, x, y, rot, 0.0, 0, 3.0, 6.0, 1.6, 3.5, '#bfc3c7', order=1, tag=t)
        for ly in (-2.0, 2.0):
            self.box(g, x, y, rot, 0.7, ly, 1.0, 1.0, 0, 0.2, TIN, order=-1)
        for pressed, dx in ((False, -2.05), (True, -1.6)):
            self.box(g, x, y, rot, dx, 0, 1.1, 2.2, 1.0, 2.6, '#2b2b2b', order=2, only=(ref, pressed), tag=t)

    def _usb(self, x, y):
        g = self.group('J102', 'T')
        self.box(g, x, y - 2.0, 0, 0, 0, 7.5, 5.4, 0, 2.6, '#c8ccd0', tag='h:J102')
        self.box(g, x, y + 0.72, 0, 0, 0, 6.6, 0.05, 0.45, 2.15, '#202020', order=1, tag='h:J102')

    def _build(self):
        self._build_board()
        P = {p[0]: p for p in B.PARTS}
        shunts = []
        skip = {'XU1', 'J1', 'J2', 'J3', 'J8', 'S1', 'S2', 'J102', 'J100', 'H1', 'H2'}
        for ref, fp, x, y, rot, side, h in B.PARTS:
            if ref in skip or ref.startswith('MH'):
                continue
            g = self.group(ref, 'T')
            kind = ref.rstrip('0123456789')
            if fp in ('0402', '0603', '0805_HV', '1206'):
                L, W, H = {'0402': (1.0, 0.5, 0.35), '0603': (1.6, 0.8, 0.45),
                           '0805_HV': (2.0, 1.25, 1.1), '1206': (3.2, 1.6, 0.55)}[fp]
                self._passive(g, ref, x, y, rot, L, W, H, kind)
            elif fp == '3216-18':
                self._tantalum(g, x, y, rot)
            elif fp.startswith('WL-SMCW') or fp == '19-337_RGB':
                self._led(g, ref, x, y, rot, rgb=fp == '19-337_RGB')
            elif fp == 'SOT-23':
                self._ic(g, x, y, rot, 2.9, 1.3, 1.0, legs=((-0.95, -0.9, 0.4, 0.6), (0.95, -0.9, 0.4, 0.6), (0, 0.9, 0.4, 0.6)))
            elif fp == 'SOT-323':
                self._ic(g, x, y, rot, 2.0, 1.25, 0.9, legs=((-0.65, -0.85, 0.3, 0.5), (0.65, -0.85, 0.3, 0.5), (0, 0.85, 0.3, 0.5)))
            elif fp == 'SOD-123':
                self._ic(g, x, y, rot, 2.7, 1.6, 1.1, legs=((-1.55, 0, 0.5, 0.6), (1.55, 0, 0.5, 0.6)), dot=False)
                self.box(g, x, y, rot, -0.95, 0, 0.35, 1.6, 1.1, 1.11, '#9a9a9a', order=1)
            elif fp == 'DCK0006A_N':
                self._ic(g, x, y, rot, 1.25, 2.0, 0.9, legs=tuple((sx * 0.9, sy * 0.65, 0.5, 0.25) for sx in (-1, 1) for sy in (-1, 0, 1)))
            elif fp == 'DRL0005A':
                self._ic(g, x, y, rot, 1.2, 1.6, 0.55)
            elif fp == 'DRV0006A':
                self._ic(g, x, y, rot, 2.0, 2.0, 0.75)
            elif fp == 'DPU0014A':
                self._ic(g, x, y, rot, 3.0, 2.0, 0.6)
            elif fp == 'RSA0016B':
                self._ic(g, x, y, rot, 4.0, 4.0, 0.9)
            elif fp == 'RGC0064B':
                self._ic(g, x, y, rot, 9.0, 9.0, 0.9, color='#2e2f31')
            elif fp == 'ECS_ECX_31B':
                self.box(g, x, y, rot, 0, 0, 3.2, 1.5, 0, 0.35, '#c9b48a')
                self.box(g, x, y, rot, 0, 0, 3.0, 1.3, 0.35, 0.9, '#d4d7da', order=1)
            elif fp == 'Murata_CSTCR':
                self.box(g, x, y, rot, 0, 0, 4.5, 2.0, 0, 1.1, '#d6c79f')
                for lx in (-1.9, 0, 1.9):
                    self.box(g, x, y, rot, lx, 0, 0.5, 2.1, 0, 0.25, TIN, order=-1)
            elif fp == 'CBC2518':
                self.box(g, x, y, rot, 0, 0, 2.5, 1.8, 0, 1.8, '#353535')
                for lx in (-1.15, 1.15):
                    self.box(g, x, y, rot, lx, 0, 0.3, 1.8, 0, 0.6, TIN, order=-1)
            elif fp.startswith('PEC03SAAN') or fp.startswith('TSW-102'):
                n = 3 if fp.startswith('PEC03') else 2
                self._male_header(g, x, y, rot, n, 1, h, TIN if fp.startswith('PEC') else GOLD)
            elif fp.startswith('PEC07DAAN'):
                self._male_header(g, x, y, rot, 7, 2, h, TIN)
            elif fp == 'SNT-100-BK-G':
                self.groups.remove(g)
                shunts.append((ref, x, y, rot))
                continue
            else:
                self.groups.remove(g)
        # J8 (RGB jumper'lari): basliktan degil, shunt konumlarindan yerlestirilir (2x3, 2.54 mm)
        sh = [P[f'SH-J8-{i}'] for i in (1, 2, 3)]
        jx, jy = sum(p[2] for p in sh) / 3, sum(p[3] for p in sh) / 3
        self._male_header(self.group('J8', 'T'), jx, jy, 0, 2, 3, 8.38, GOLD)
        byname = {g.name: g for g in self.groups}
        for ref, x, y, rot in shunts:
            role = tag = None
            if ref == 'SH-J101-4':
                role, tag = ('shunt', 'RXD'), 'h:RXD'
            elif ref == 'SH-J101-3':
                role, tag = ('shunt', 'TXD'), 'h:TXD'
            self._shunt(byname[ref.split('-')[1]], x, y, rot, role, tag)      # SH-J101-4 -> J101
        self._dip(P['XU1'][2], P['XU1'][3])
        self._stack_header('J1', P['J1'][2], P['J1'][3], sorted(J1_MAP.items()))
        self._stack_header('J2', P['J2'][2], P['J2'][3], sorted(J2_MAP.items(), reverse=True))
        self._stack_header('J3', P['J3'][2], P['J3'][3], sorted(J3_MAP.items()))
        for ref in ('S1', 'S2'):
            self._switch(ref, P[ref][2], P[ref][3], P[ref][4])
        self._usb(P['J102'][2], P['J102'][3])
        for ref in ('H1', 'H2'):
            g = self.group(ref, 'B')
            self.prism(g, P[ref][2], P[ref][3], 2.4, -self.T - 10.0, -self.T, 10, '#ecebe4')
        # yuzey detaylari: padler, delikler, silkscreen
        for flat in B.PADS_TOP:
            self.decal('T', 'poly', flat, GOLD, hq=True)
        for p in B.PARTS:
            if p[0].startswith('MH'):
                for side in 'TB':
                    self.disc(side, p[2], p[3], 2.15, '#8c8c86', n=20)
                    self.disc(side, p[2], p[3], 1.6, '#101010', n=20, z=(0.006 if side == 'T' else -self.T - 0.006))
        for flat in B.SILK_TOP_FILL:
            self.decal('T', 'poly', flat, SILK, hq=True)
        for w, flat in B.SILK_TOP:
            self.decal('T', 'line', flat, SILK, width=w, hq=w < 0.15)
        for flat in B.SILK_BOT_FILL:
            self.decal('B', 'poly', flat, SILK, hq=True)
        for w, flat in B.SILK_BOT:
            self.decal('B', 'line', flat, SILK, width=w, hq=True)


# ---------------------------------------------------------------- kamera
class Camera:
    def __init__(self):
        self.target = [B.W / 2, B.H / 2, 0.0]
        self.yaw, self.pitch, self.dist, self.fov = -22.0, 48.0, 175.0, 34.0
        self.w, self.h = 900, 700

    def preset(self, name):
        self.target = [B.W / 2, B.H / 2, 0.0]
        self.yaw, self.pitch, self.dist = {'3d': (-22.0, 48.0, 175.0), 'top': (0.0, 89.9, 155.0),
                                           'bottom': (0.0, -89.9, 155.0), 'front': (0.0, 12.0, 165.0)}[name]

    def basis(self):
        yw, pt = math.radians(self.yaw), math.radians(self.pitch)
        fwd = (math.cos(pt) * math.sin(yw), math.cos(pt) * math.cos(yw), -math.sin(pt))
        cam = tuple(self.target[i] - fwd[i] * self.dist for i in range(3))
        r = _norm((fwd[1], -fwd[0], 0.0)) if abs(fwd[2]) < 0.99999 else (math.cos(yw), -math.sin(yw), 0.0)
        u = (r[1] * fwd[2] - r[2] * fwd[1], r[2] * fwd[0] - r[0] * fwd[2], r[0] * fwd[1] - r[1] * fwd[0])
        return cam, r, u, fwd

    def focal(self):
        return self.h / (2 * math.tan(math.radians(self.fov) / 2))

    def project(self, V):
        """-> (xs, ys, zs) ekran koordinatlari + derinlik; kameranin arkasi icin derinlik <= 0."""
        (cx, cy, cz), (rx, ry, rz), (ux, uy, uz), (fx, fy, fz) = self.basis()
        foc, w2, h2 = self.focal(), self.w / 2, self.h / 2
        xs, ys, zs = [], [], []
        ax, ay, az = xs.append, ys.append, zs.append
        for x, y, z in V:
            dx, dy, dz = x - cx, y - cy, z - cz
            d = dx * fx + dy * fy + dz * fz
            k = foc / d if d > 1.0 else foc
            ax(w2 + (dx * rx + dy * ry + dz * rz) * k)
            ay(h2 - (dx * ux + dy * uy + dz * uz) * k)
            az(d)
        return xs, ys, zs

    def pan(self, dx_px, dy_px):
        _, r, u, _ = self.basis()
        s = self.dist / self.focal()
        for i in range(3):
            self.target[i] += (-r[i] * dx_px + u[i] * dy_px) * s
        self.target[2] = max(-15.0, min(15.0, self.target[2]))


# ---------------------------------------------------------------- Tk penceresi
class Board3D:
    """Simulatore bagli 3D kart penceresi. app: gui.App (cpu, running, do_reset, do_run)."""

    def __init__(self, app):
        import tkinter as tk
        from tkinter import ttk
        self.app = app
        self.scene = Scene()
        self.cam = Camera()
        self.win = w = tk.Toplevel(app)
        w.title('MSP-EXP430G2ET 3D')
        w.geometry('960x760')
        w.protocol('WM_DELETE_WINDOW', self.close)
        bar = ttk.Frame(w, padding=4)
        bar.pack(fill='x')
        for t, v in (('3D', '3d'), ('Ust', 'top'), ('Alt', 'bottom'), ('Yan', 'front')):
            ttk.Button(bar, text=t, width=5, command=lambda v=v: self.view(v)).pack(side='left', padx=2)
        self.show_levels = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text='Pin seviyeleri', variable=self.show_levels,
                        command=self._levels_toggled).pack(side='left', padx=10)
        self.legend = tk.Canvas(bar, height=18, width=330, highlightthickness=0, bg='#2b2f36')
        self.legend.pack(side='left')
        x = 4
        for key, txt in (('out1', 'cikis 1'), ('out0', 'cikis 0'), ('in1', 'giris 1'), ('in0', 'giris 0')):
            self.legend.create_rectangle(x, 4, x + 10, 14, fill=PIN_COL[key], outline='#555')
            self.legend.create_text(x + 14, 9, text=txt, anchor='w', fill='#e0e0e0', font=('TkDefaultFont', 10))
            x += 80
        self.cv = tk.Canvas(w, bg=BG, highlightthickness=0)
        self.cv.pack(fill='both', expand=True)
        self.info = tk.StringVar(value='Sol tik + surukle: dondur   Sag tik / Shift + surukle: kaydir   '
                                       'Tekerlek: yakinlas   S1 (P1.3) ve S2 (RESET) tiklanabilir')
        ttk.Label(w, textvariable=self.info, anchor='w', relief='sunken').pack(fill='x', side='bottom')
        self.pressed = {'S1': False, 'S2': False}
        self.flash_until = {'TXD': 0.0, 'RXD': 0.0}
        self.dyn = {}
        self.state = {}
        self._drag = None
        self._pending = None
        self._hq_job = None
        self._flash_job = None
        self._hud = None
        c = self.cv
        c.bind('<Configure>', self._resize)
        c.bind('<ButtonPress-1>', self._b1_down)
        c.bind('<B1-Motion>', self._b1_move)
        c.bind('<ButtonRelease-1>', self._b1_up)
        for b in ('2', '3'):
            c.bind(f'<ButtonPress-{b}>', lambda e: self._start(e, 'pan'))
            c.bind(f'<B{b}-Motion>', self._move)
            c.bind(f'<ButtonRelease-{b}>', self._end)
        c.bind('<MouseWheel>', lambda e: self._zoom(1 if e.delta > 0 else -1))
        c.bind('<Button-4>', lambda e: self._zoom(1))
        c.bind('<Button-5>', lambda e: self._zoom(-1))
        c.bind('<Motion>', self._hover)
        w.bind('<Key-r>', lambda e: self.view('3d'))

    # --- dis API ---
    def alive(self):
        try:
            return bool(self.win.winfo_exists())
        except Exception:
            return False

    def lift(self):
        self.win.deiconify()
        self.win.lift()
        self.win.focus_set()

    def close(self):
        if self.pressed['S1']:
            self.app.cpu.p1.set_input(3, 1)
        self.win.destroy()
        if getattr(self.app, 'board3d', None) is self:
            self.app.board3d = None

    def flash(self, kind):
        self.flash_until[kind] = time.perf_counter() + 0.12
        self.update_state()
        if self._flash_job is None:
            self._flash_job = self.win.after(140, self._flash_end)

    def _flash_end(self):
        self._flash_job = None
        self.update_state()
        if any(t > time.perf_counter() for t in self.flash_until.values()):
            self._flash_job = self.win.after(60, self._flash_end)

    def view(self, name):
        self.cam.preset(name)
        self.redraw()

    # --- durum -> renkler ---
    def _compute_state(self):
        cpu = self.app.cpu
        pins = pin_states(cpu)
        st = {}
        lv = led_levels(pins)
        st[('lens', 'D1')] = lv['D1']
        st[('lens', 'D2')] = lv['D2']
        st[('lens', 'D3')] = lv['D3']
        st[('lens', 'D100')] = 1.0 if self.app.running else 0.0
        st[('lens', 'D101')] = 1.0
        st[('lens', 'D102')] = 1.0
        for ref in LEDS:
            st[('spill', ref)] = st[('lens', ref)]
        show = self.show_levels.get()
        for g, mp in (('J1', J1_MAP), ('J2', J2_MAP), ('XU1', DIP_MAP)):
            for num, sig in mp.items():
                st[('pin', (g, num))] = pin_class(pins[sig]) if show and isinstance(sig, tuple) else None
        now = time.perf_counter()
        for k in ('TXD', 'RXD'):
            st[('shunt', k)] = self.flash_until[k] > now
        self._pins = pins
        return st

    def _role_fill(self, role, val):
        """(renk veya None=varsayilan, gorunur mu)"""
        kind, key = role
        if kind == 'lens' or kind == 'spill':
            col = LEDS[key][0]
            if col == 'rgb':
                r, g, b = val
                lit = r or g or b
                on = _hex(255 * r, 255 * g + 40 * (r and not g), 255 * b) if lit else None
                if kind == 'lens':
                    return (mix('#ffffff', on, 0.85) if lit else '#e6e6e6'), True
                return on, bool(lit)
            if kind == 'lens':
                return (mix(LED_OFF[col], LED_ON[col], val) if val else LED_OFF[col]), True
            return LED_ON[col], val > 0
        if kind == 'pin':
            return (PIN_COL[val] if val else None), True
        if kind == 'shunt':
            return (FLASH[key] if val else None), True
        return None, True

    def update_state(self):
        if not self.alive():
            return
        st = self._compute_state()
        for role, val in st.items():
            if self.state.get(role, object()) == val:
                continue
            self.state[role] = val
            for item, base, k, kind in self.dyn.get(role, ()):
                col, vis = self._role_fill(role, val)
                if kind == 'face':
                    f = shade(col, k) if col else shade(base, k)
                    self.cv.itemconfigure(item, fill=f, outline=f)
                else:                                     # spill decal
                    if vis and col:
                        self.cv.itemconfigure(item, state='normal', fill=add(PCB, col, base))
                    else:
                        self.cv.itemconfigure(item, state='hidden')
        self._update_hud()

    def _update_hud(self):
        if not self._hud:
            return
        cpu, app = self.app.cpu, self.app
        if app.running:
            mode = 'LPM (uyku)' if cpu.r[2] & 0x10 else 'Calisiyor'
        else:
            mode = {'halt': 'Durdu (jmp $)', 'break': 'Breakpoint', 'sleep': 'Uyuyor'}.get(cpu.stop, 'Duraklatildi')
        txt = f'{mode}   PC={cpu.r[0]:04X}   {cpu.cycles} cycle'
        self.cv.itemconfigure(self._hud, text=txt)

    def _levels_toggled(self):
        self.update_state()

    # --- cizim ---
    def _resize(self, e):
        self.cam.w, self.cam.h = max(e.width, 50), max(e.height, 50)
        self.redraw()

    def redraw(self, hq=True):
        if self._pending:
            self.win.after_cancel(self._pending)
            self._pending = None
        self.render(hq)

    def request(self, hq=False):
        if self._pending is None:
            self._pending = self.win.after_idle(self._do_pending, hq)

    def _do_pending(self, hq):
        self._pending = None
        self.render(hq)

    def render(self, hq=True):
        sc, cam, cv = self.scene, self.cam, self.cv
        t0 = time.perf_counter()
        cv.delete('all')
        self.dyn = {}
        self.state = self._compute_state()
        xs, ys, zs = cam.project(sc.V)
        C, r, u, f = cam.basis()
        scale = cam.focal() / cam.dist
        above = C[2] > -sc.T / 2
        create = cv.create_polygon

        def face_list(faces):
            out = []
            for face in faces:
                idx, n, d = face[0], face[1], face[2]
                if n[0] * C[0] + n[1] * C[1] + n[2] * C[2] - d <= 1e-6:
                    continue
                if min(zs[i] for i in idx) <= 1.0:
                    continue
                out.append(face)
            return out

        def draw_face(face, tags=()):
            idx, _, _, base, k, fill, role = face
            coords = []
            for i in idx:
                coords.append(xs[i])
                coords.append(ys[i])
            if role:
                val = self.state.get(role)
                col, _ = self._role_fill(role, val)
                if col:
                    fill = shade(col, k)
            it = create(coords, fill=fill, outline=fill, tags=tags)
            if role:
                self.dyn.setdefault(role, []).append((it, base, k, 'face'))

        # golge (zemin)
        if above and C[2] > -11.6:
            cv.create_polygon([v for i in sc.shadow for v in (xs[i], ys[i])], fill=SHADOW, outline=SHADOW)

        def draw_groups(side):
            gs = []
            for g in sc.groups:
                if g.side != side:
                    continue
                dx = max(g.lo[0] - C[0], 0.0, C[0] - g.hi[0])
                dy = max(g.lo[1] - C[1], 0.0, C[1] - g.hi[1])
                dz = max(g.lo[2] - C[2], 0.0, C[2] - g.hi[2])
                gs.append((dx * dx + dy * dy + dz * dz, g))
            gs.sort(key=lambda t: -t[0])
            for _, g in gs:
                boxes = [b for b in g.boxes if b.only is None or self.pressed.get(b.only[0]) == b.only[1]]
                if side == 'B' and above or side == 'T' and not above:
                    boxes.sort(key=lambda b: (-b.order, -self._depth(b.center, C, f)))
                else:
                    boxes.sort(key=lambda b: (b.order, -self._depth(b.center, C, f)))
                for b in boxes:
                    tags = (b.tag,) if b.tag else ()
                    for face in face_list(b.faces):
                        draw_face(face, tags)
                if g.label and side == 'T' and above:
                    self._draw_label(g.label, xs, ys, cam, scale)

        def draw_board():
            sides = face_list(sc.board_sides)
            sides.sort(key=lambda fc: -sum(zs[i] for i in fc[0]))
            for face in sides:
                draw_face(face)
            idx, fill = sc.board_top if above else sc.board_bot
            cv.create_polygon([v for i in idx for v in (xs[i], ys[i])], fill=fill, outline=fill)

        def draw_decals(side):
            for kind, idx, color, width, role, dq in sc.decals[side]:
                if dq and not hq:
                    continue
                coords = [v for i in idx for v in (xs[i], ys[i])]
                if kind == 'line':
                    lw = width * scale
                    if lw < 0.35 and dq:
                        continue
                    cv.create_line(coords, fill=color, width=max(1.0, lw), capstyle='round', joinstyle='round')
                else:
                    if role:
                        col, vis = self._role_fill(role, self.state.get(role))
                        t = 0.3 if len(idx) >= 18 else 0.65
                        it = cv.create_polygon(coords, fill=add(PCB, col, t) if col else color, outline='',
                                               state='normal' if vis and col else 'hidden')
                        self.dyn.setdefault(role, []).append((it, t, 1.0, 'spill'))
                    else:
                        cv.create_polygon(coords, fill=color, outline='')

        if above:
            draw_groups('B')
            draw_board()
            draw_decals('T')
            draw_groups('T')
        else:
            draw_groups('T')
            draw_board()
            draw_decals('B')
            draw_groups('B')
        self._hud = cv.create_text(12, 12, anchor='nw', fill='#e8e8e8', font=('TkFixedFont', 12), text='')
        cv.create_text(12, cam.h - 10, anchor='sw', fill='#8a9099', font=('TkDefaultFont', 10),
                       text='MSP-EXP430G2ET  (58.4 x 78.7 mm, TI tasarim dosyalarindan)')
        self._update_hud()
        self.last_ms = (time.perf_counter() - t0) * 1000
        if not hq:
            if self._hq_job:
                self.win.after_cancel(self._hq_job)
            self._hq_job = self.win.after(180, self._hq_render)

    def _hq_render(self):
        self._hq_job = None
        if self._drag is None:
            self.render(True)

    @staticmethod
    def _depth(p, C, f):
        return (p[0] - C[0]) * f[0] + (p[1] - C[1]) * f[1] + (p[2] - C[2]) * f[2]

    def _draw_label(self, label, xs, ys, cam, scale):
        (p0, p1, text, size) = label
        sx, sy, sz = cam.project([p0, p1])
        if min(sz) <= 1.0:
            return
        px = size * cam.focal() / sz[0]
        if px < 6:
            return
        # yazi yonu: cipin uzun ekseni boyunca, centik solda olacak sekilde (pin 1 -> asagi)
        ang = math.degrees(math.atan2(-(sy[1] - sy[0]), sx[1] - sx[0]))
        self.cv.create_text(sx[0], sy[0], text=text, angle=ang, fill='#b8b8b8',
                            font=('Helvetica', -int(px), 'bold'))

    # --- fare ---
    def _tag_under(self):
        for it in self.cv.find_withtag('current'):
            for t in self.cv.gettags(it):
                if t.startswith('h:'):
                    return t[2:]
        return None

    def _b1_down(self, e):
        t = self._tag_under()
        if t in ('S1', 'S2'):
            self.pressed[t] = True
            if t == 'S1':
                self.app.cpu.p1.set_input(3, 0)         # S1: P1.3'u GND'ye ceker
            self._drag = ('button', t)
            self.redraw()
            self.app.refresh()
            return
        self._start(e, 'pan' if e.state & 1 else 'rot')

    def _b1_move(self, e):
        if self._drag and self._drag[0] != 'button':
            self._move(e)

    def _b1_up(self, e):
        if self._drag and self._drag[0] == 'button':
            t = self._drag[1]
            self.pressed[t] = False
            self._drag = None
            if t == 'S1':
                self.app.cpu.p1.set_input(3, 1)
                self.app.refresh()
            else:
                self._reset_pressed()
            self.redraw()
            return
        self._end(e)

    def _reset_pressed(self):
        app = self.app
        was = app.running
        app.do_reset()
        if was:
            app.do_run()

    def _start(self, e, mode):
        self._drag = (mode, e.x, e.y)

    def _move(self, e):
        if not self._drag or self._drag[0] == 'button':
            return
        mode, x0, y0 = self._drag
        dx, dy = e.x - x0, e.y - y0
        self._drag = (mode, e.x, e.y)
        if mode == 'rot':
            self.cam.yaw = (self.cam.yaw + dx * 0.45) % 360
            self.cam.pitch = max(-89.9, min(89.9, self.cam.pitch + dy * 0.35))
        else:
            self.cam.pan(dx, dy)
        self.request(hq=False)

    def _end(self, e):
        self._drag = None
        if self._hq_job is None:
            self.redraw()

    def _zoom(self, d):
        self.cam.dist = max(25.0, min(600.0, self.cam.dist * (0.88 if d > 0 else 1 / 0.88)))
        self.request(hq=False)

    def _hover(self, e):
        t = self._tag_under()
        if not t:
            return
        pins = getattr(self, '_pins', None) or pin_states(self.app.cpu)
        if t.startswith('pin:'):
            _, g, num = t.split(':')
            num = int(num)
            sig = {'J1': J1_MAP, 'J2': J2_MAP, 'J3': J3_MAP, 'XU1': DIP_MAP}[g][num]
            where = f'{g}.{num}' if g != 'XU1' else f'XU1 pin {num}'
            if isinstance(sig, tuple):
                lvl, out = pins[sig]
                s = f'{where}   {sig_name(sig)}   {"cikis" if out else "giris"} = {lvl}'
            else:
                s = f'{where}   {sig}'
        elif t in LEDS:
            col, src, jmp = LEDS[t]
            ad = {'green': 'yesil', 'red': 'kirmizi', 'yellow': 'sari', 'rgb': 'RGB'}[col]
            if isinstance(src, tuple) and isinstance(src[0], tuple):
                s = f'{t} {ad} LED  ({jmp}: R=P2.1  G=P2.3  B=P2.5)'
            elif src:
                s = f'{t} {ad} LED  ({sig_name(src)}, jumper {jmp})'
            else:
                s = f'{t} {ad} LED  ({jmp})'
        else:
            s = {'S1': 'S1: P1.3 kullanici butonu (basili tut = 0)', 'S2': 'S2: RESET butonu',
                 'XU1': 'XU1: MSP430G2553IN20 (DIP-20 soket)', 'J102': 'J102: micro-USB (eZ-FET)',
                 'TXD': 'J101 TXD>> : hedef UART cikisi (UCA0TXD, P1.2)',
                 'RXD': 'J101 RXD<< : hedef UART girisi (UCA0RXD, P1.1)'}.get(t, t)
        self.info.set(s)
