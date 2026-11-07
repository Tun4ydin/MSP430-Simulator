"""MSP430G2553 cekirdegi + cevre birimleri (GPIO, Timer_A, WDT, UART). GUI bagimliligi yok."""

GIE, CPUOFF = 0x08, 0x10
ACLK_DIV = 83      # kalibrasyon: MCLK 1 MHz / VLO ~12 kHz
UART_BITS = 10     # kalibrasyon: karakter basina bit

RESET_VEC = 0xFFFE
VECTORS = dict(PORT1=0xFFE4, PORT2=0xFFE6, ADC10=0xFFEA, USCIAB0TX=0xFFEC, USCIAB0RX=0xFFEE,
               TIMER0_A1=0xFFF0, TIMER0_A0=0xFFF2, WDT=0xFFF4, COMPARATORA=0xFFF6,
               TIMER1_A1=0xFFF8, TIMER1_A0=0xFFFA, NMI=0xFFFC, RESET=0xFFFE)


def _symbols():
    s = {f'BIT{i:X}': 1 << i for i in range(16)}
    s.update({f'{k}_VECTOR': v for k, v in VECTORS.items()})
    s.update(IE1=0, IE2=1, IFG1=2, IFG2=3, WDTIE=1, WDTIFG=1, NMIIE=0x10, OFIE=2,
             UCA0RXIE=1, UCA0TXIE=2, UCA0RXIFG=1, UCA0TXIFG=2,
             P1IN=0x20, P1OUT=0x21, P1DIR=0x22, P1IFG=0x23, P1IES=0x24, P1IE=0x25, P1SEL=0x26,
             P1REN=0x27, P2IN=0x28, P2OUT=0x29, P2DIR=0x2A, P2IFG=0x2B, P2IES=0x2C, P2IE=0x2D,
             P2SEL=0x2E, P2REN=0x2F, P1SEL2=0x41, P2SEL2=0x42,
             BCSCTL3=0x53, DCOCTL=0x56, BCSCTL1=0x57, BCSCTL2=0x58,
             CALDCO_1MHZ=0x10FE, CALBC1_1MHZ=0x10FF,
             CALDCO_16MHZ=0x10F8, CALBC1_16MHZ=0x10F9,
             CALDCO_12MHZ=0x10FA, CALBC1_12MHZ=0x10FB,
             CALDCO_8MHZ=0x10FC, CALBC1_8MHZ=0x10FD,
             # Eski / kisa TimerA adlari (TI kodlari icin)
             TACTL=0x160, TACCTL0=0x162, TACCTL1=0x164, TACCTL2=0x166,
             TAR=0x170, TACCR0=0x172, TACCR1=0x174, TACCR2=0x176, TAIV=0x12E,
             # Temel saat sistemi bitleri
             DCO0=0x20, DCO1=0x40, DCO2=0x80,
             RSEL0=1, RSEL1=2, RSEL2=4, RSEL3=8,
             DIVA0=0x10, DIVA1=0x20, DIVA_0=0, DIVA_1=0x10, DIVA_2=0x20, DIVA_3=0x30,
             DIVS_0=0, DIVS_1=0x02, DIVS_2=0x04, DIVS_3=0x06,
             DIVM_0=0, DIVM_1=0x10, DIVM_2=0x20, DIVM_3=0x30,
             SELM_0=0, SELM_1=0x40, SELM_2=0x80, SELM_3=0xC0, SELS=0x08,
             LFXT1S0=0x10, LFXT1S1=0x20, LFXT1S_0=0, LFXT1S_1=0x10, LFXT1S_2=0x20, LFXT1S_3=0x30,
             XCAP0=0x04, XCAP1=0x08, XCAP_0=0, XCAP_1=0x04, XCAP_2=0x08, XCAP_3=0x0C, XTS=0x40,
             # WDT modlari
             WDT_ARST_1000=0x5A0C, WDT_ARST_250=0x5A0D, WDT_ARST_16=0x5A0E, WDT_ARST_1_9=0x5A0F,
             WDT_MRST_32=0x5A08, WDT_MRST_8=0x5A09, WDT_MRST_0_5=0x5A0A, WDT_MRST_0_064=0x5A0B,
             WDT_ADLY_1000=0x5A1C, WDT_ADLY_250=0x5A1D, WDT_ADLY_16=0x5A1E, WDT_ADLY_1_9=0x5A1F,
             # USCI modlari ve bitleri
             UCMODE_0=0, UCMODE_1=2, UCMODE_2=4, UCMODE_3=6,
             UCSYNC=1, UC7BIT=0x10, UCMSB=0x20, UCPAR=0x40, UCPEN=0x80, UCSPB=0x08,
             UCMST=0x08, UCCKPH=0x80, UCCKPL=0x40, UCOS16=1,
             # ADC10 / Timer1 / USCI_B sembolleri (derleme uyumlulugu; cevre birimi simule edilmez)
             ADC10CTL0=0x1B0, ADC10CTL1=0x1B2, ADC10MEM=0x1B4, ADC10AE0=0x4A,
             ADC10SC=1, ENC=2, ADC10ON=0x10, INCH_10=0xA000,
             TA1CTL=0x180, TA1CCTL0=0x182, TA1CCR0=0x192, TA1R=0x190, TA1IV=0x11E,
             UCB0CTL0=0x68, UCB0CTL1=0x69, UCB0BR0=0x6A, UCB0BR1=0x6B,
             UCB0RXBUF=0x6E, UCB0TXBUF=0x6F,
             # Flash denetleyici
             FCTL1=0x128, FCTL2=0x12A, FCTL3=0x12C, FWKEY=0xA500,
             # Bayrak kisayollari
             C=1, Z=2, N=4, V=0x100,
             UCA0CTL0=0x60, UCA0CTL1=0x61, UCA0BR0=0x62, UCA0BR1=0x63, UCA0MCTL=0x64,
             UCA0STAT=0x65, UCA0RXBUF=0x66, UCA0TXBUF=0x67, UCSWRST=1, UCSSEL_2=0x80, UCSSEL_1=0x40,
             UCSSEL0=0x40, UCSSEL1=0x80,
             WDTCTL=0x120, WDTPW=0x5A00, WDTHOLD=0x80, WDTNMI=0x20, WDTCNTCL=8, WDTTMSEL=0x10,
             WDTSSEL=4, WDTIS0=1, WDTIS1=2,
             WDT_MDLY_32=0x5A18, WDT_MDLY_8=0x5A19, WDT_MDLY_0_5=0x5A1A, WDT_MDLY_0_064=0x5A1B,
             TA0IV=0x12E, TA0CTL=0x160, TA0CCTL0=0x162, TA0CCTL1=0x164, TA0CCTL2=0x166,
             TA0R=0x170, TA0CCR0=0x172, TA0CCR1=0x174, TA0CCR2=0x176,
             TACLR=4, TAIE=2, TAIFG=1, CCIE=0x10, CCIFG=1, CAP=0x100,
             TAIV_TACCR1=2, TAIV_TACCR2=4, TAIV_TAIFG=10,
             GIE=8, CPUOFF=0x10, OSCOFF=0x20, SCG0=0x40, SCG1=0x80,
             LPM0_bits=0x10, LPM1_bits=0x50, LPM2_bits=0x90, LPM3_bits=0xD0, LPM4_bits=0xF0,
             __STACK_END=0x0400)
    for i in range(4):
        s[f'TASSEL_{i}'] = i << 8
        s[f'ID_{i}'] = i << 6
        s[f'MC_{i}'] = i << 4
    for i in range(8):
        s[f'OUTMOD_{i}'] = i << 5
    return s


SYMBOLS = _symbols()


class Mem:
    """64 KB bellek. Cevre birimleri io8/io16 sozluklerinden baglanir."""

    def __init__(self, log):
        self.b = bytearray(0x10000)
        self.io8, self.io16, self.log, self.warned = {}, {}, log, set()

    def reg8(self, a, rd, wr, peek=None):
        self.io8[a] = (rd, wr, peek or rd)

    def reg16(self, a, rd, wr, peek=None):
        self.io16[a] = (rd, wr, peek or rd)

    def rb(self, a, peek=False):
        h = self.io8.get(a)
        if h:
            return h[2 if peek else 0]()
        h = self.io16.get(a & ~1)
        if h:
            return (h[2 if peek else 0]() >> (8 * (a & 1))) & 0xFF
        return 0 if a < 0x200 else self.b[a]

    def rw(self, a, peek=False):
        a &= 0xFFFE
        h = self.io16.get(a)
        if h:
            return h[2 if peek else 0]()
        if a < 0x200:
            return self.rb(a, peek) | self.rb(a + 1, peek) << 8
        return self.b[a] | self.b[a + 1] << 8

    def wb(self, a, v):
        v &= 0xFF
        h = self.io8.get(a)
        if h:
            h[1](v)
            return
        h = self.io16.get(a & ~1)
        if h:
            sh = 8 * (a & 1)
            h[1]((h[2]() & ~(0xFF << sh)) | v << sh)
        elif 0x200 <= a < 0x400:
            self.b[a] = v
        elif a >= 0x200:
            self._ro(a)

    def ww(self, a, v):
        a &= 0xFFFE
        v &= 0xFFFF
        h = self.io16.get(a)
        if h:
            h[1](v)
        elif a < 0x200:
            self.wb(a, v & 0xFF)
            self.wb(a + 1, v >> 8)
        elif a < 0x400:
            self.b[a], self.b[a + 1] = v & 0xFF, v >> 8
        else:
            self._ro(a)

    def _ro(self, a):
        if a not in self.warned and len(self.warned) < 20:
            self.warned.add(a)
            kind = 'flash' if a >= 0xC000 or 0x1000 <= a < 0x1100 else 'bos/bagli olmayan bellek'
            self.log.append(f'Uyari: 0x{a:04X} adresine yazma yok sayildi ({kind}). Degiskenler RAM (0x0200-0x03FF) icinde olmali.')


class Periph:
    def reset(self): pass
    def tick(self, n): pass
    def next_event(self): return None
    def pending(self): return ()
    def ack(self, vec): pass


class Plain(Periph):
    """Sadece saklanan register'lar (BCS, SEL2, UART yardimcilari)."""
    DEFAULTS = {0x41: 0, 0x42: 0, 0x53: 4, 0x56: 0, 0x57: 0x87, 0x58: 0, 0x5D: 0, 0x5E: 0, 0x5F: 0,
                0x60: 0, 0x64: 0, 0x65: 0}

    def __init__(self, mem):
        self.v = {}
        for a in self.DEFAULTS:
            mem.reg8(a, lambda a=a: self.v[a], lambda x, a=a: self.v.__setitem__(a, x))
        self.reset()

    def reset(self):
        self.v = dict(self.DEFAULTS)


class Port(Periph):
    def __init__(self, mem, base, vec, ext=0):
        self.vec, self.ext0, self.ext = vec, ext, ext
        self.drv = ext             # disaridan surulen pinler; digerleri yuzer (PxREN ile pull-up/down)
        self.rg = [0] * 8          # in(kullanilmaz) out dir ifg ies ie sel ren
        mem.reg8(base, lambda: self.pins(), lambda v: None)
        for i in range(1, 8):
            mem.reg8(base + i, lambda i=i: self.rg[i], lambda v, i=i: self._w(i, v))
        self.old = self.pins()

    def pins(self):
        pull = self.rg[7] & self.rg[1] & ~self.drv        # PxREN=1: PxOUT yonunde pull-up/down
        inp = (self.ext & self.drv) | pull
        return ((self.rg[1] & self.rg[2]) | (inp & ~self.rg[2])) & 0xFF

    def _w(self, i, v):
        self.rg[i] = v
        if i in (1, 2, 7):
            self._upd()

    def _upd(self):
        new = self.pins()
        ch = new ^ self.old
        self.rg[3] |= (ch & new & ~self.rg[4]) | (ch & ~new & self.rg[4])
        self.rg[3] &= 0xFF
        self.old = new

    def set_input(self, bit, level):
        """level 0/1 = pini surer, None = birakir (yuzer; PxREN varsa pull-up/down)."""
        self.drv = self.drv & ~(1 << bit) if level is None else self.drv | 1 << bit
        self.ext =(self.ext | 1 << bit) if level else (self.ext & ~(1 << bit))
        self._upd()

    def reset(self):
        self.rg = [0] * 8
        self.old = self.pins()

    def pending(self):
        return (self.vec,) if self.rg[3] & self.rg[5] else ()


class TimerA(Periph):
    def __init__(self, mem):
        mem.reg16(0x160, lambda: self.ctl, self._w_ctl)
        mem.reg16(0x170, lambda: self.tar, lambda v: setattr(self, 'tar', v))
        for i in range(3):
            mem.reg16(0x162 + 2 * i, lambda i=i: self.cctl[i], lambda v, i=i: self.cctl.__setitem__(i, v))
            mem.reg16(0x172 + 2 * i, lambda i=i: self.ccr[i], lambda v, i=i: self.ccr.__setitem__(i, v))
        mem.reg16(0x12E, lambda: self._taiv(True), lambda v: self._taiv(True), lambda: self._taiv(False))
        self.reset()

    def reset(self):
        self.ctl, self.cctl, self.ccr, self.tar, self.acc, self.d = 0, [0] * 3, [0] * 3, 0, 0, 1

    def _w_ctl(self, v):
        if v & 4:
            self.tar, self.acc, self.d = 0, 0, 1
        self.ctl = v & ~4

    def _taiv(self, clear):
        for i, val in ((1, 2), (2, 4)):
            if self.cctl[i] & 0x11 == 0x11:
                if clear:
                    self.cctl[i] &= ~1
                return val
        if self.ctl & 3 == 3:
            if clear:
                self.ctl &= ~1
            return 10
        return 0

    def pending(self):
        out = []
        if self.cctl[0] & 0x11 == 0x11:
            out.append(0xFFF2)
        if self.cctl[1] & 0x11 == 0x11 or self.cctl[2] & 0x11 == 0x11 or self.ctl & 3 == 3:
            out.append(0xFFF0)
        return out

    def ack(self, vec):
        if vec == 0xFFF2:
            self.cctl[0] &= ~1

    def _per(self):
        src = (self.ctl >> 8) & 3
        if not self.ctl & 0x30 or src in (0, 3):
            return 0
        return (ACLK_DIV if src == 1 else 1) << ((self.ctl >> 6) & 3)

    def tick(self, n):
        per = self._per()
        if per:
            self.acc += n
            t, self.acc = divmod(self.acc, per)
            if t:
                self._count(t)

    def next_event(self):
        per = self._per()
        return self._dist() * per - self.acc if per else None

    def _dist(self):
        """Bir sonraki bayragin (alt sinir) kac tick sonra set olabilecegi (>=1)."""
        mc, t = (self.ctl >> 4) & 3, self.tar
        if mc == 1:
            c0 = self.ccr[0]
            if t >= c0:
                return 1
            return min([c0 - t] + [x - t for x in self.ccr[1:] if t < x <= c0])
        if mc == 2:
            return min([0x10000 - t] + [x - t for x in self.ccr if x > t])
        return 1                       # ponytail: up/down modunda tick tick ilerler, yavas ama dogru

    def _count(self, t):
        while t > 0:
            k = min(t, self._dist())
            self.tar = (self.tar + k - 1) & 0xFFFF
            self._tick1()
            t -= k

    def _tick1(self):
        mc, t, c0 = (self.ctl >> 4) & 3, self.tar, self.ccr[0]
        if mc == 1:
            if t >= c0:
                t = 0
                self.ctl |= 1
            else:
                t += 1
        elif mc == 2:
            t = (t + 1) & 0xFFFF
            if t == 0:
                self.ctl |= 1
        elif self.d > 0:
            if t >= c0:
                self.d, t = -1, max(t - 1, 0)
            else:
                t += 1
        else:
            t = max(t - 1, 0)
            if t == 0:
                self.ctl |= 1
                self.d = 1
        self.tar = t
        for i in range(3):
            if t == self.ccr[i]:
                self.cctl[i] |= 1


class WDT(Periph):
    def __init__(self, mem, cpu):
        self.cpu = cpu
        mem.reg16(0x120, lambda: 0x6900 | self.ctl, self._w)
        mem.reg8(0x00, lambda: self.ie1, lambda v: setattr(self, 'ie1', v))
        mem.reg8(0x02, lambda: self.ifg1, lambda v: setattr(self, 'ifg1', v))
        self.reset()

    def reset(self):
        self.ctl = self.cnt = self.ie1 = self.ifg1 = 0

    def _w(self, v):
        if v >> 8 != 0x5A:
            self.cpu.puc_req = 'WDT sifre ihlali (WDTCTL yazarken ust byte 0x5A olmali)'
            return
        if v & 8:
            self.cnt = 0
        self.ctl = v & 0xF7

    def _period(self):
        p = (32768, 8192, 512, 64)[self.ctl & 3]
        return p * ACLK_DIV if self.ctl & 4 else p

    def tick(self, n):
        if self.ctl & 0x80:
            return
        self.cnt += n
        p = self._period()
        if self.cnt >= p:
            if self.ctl & 0x10:
                self.ifg1 |= 1
                self.cnt %= p
            else:
                self.cpu.puc_req = 'WDT zaman asimi (program WDTCTL=WDTPW|WDTHOLD yazmadi)'

    def next_event(self):
        return None if self.ctl & 0x80 else max(1, self._period() - self.cnt)

    def pending(self):
        return (0xFFF4,) if self.ctl & 0x10 and self.ie1 & self.ifg1 & 1 else ()

    def ack(self, vec):
        self.ifg1 &= ~1


class UART(Periph):
    def __init__(self, mem):
        self.out = bytearray()     # GUI bosaltir
        self.log = mem.log
        mem.reg8(0x01, lambda: self.ie2, lambda v: setattr(self, 'ie2', v))
        mem.reg8(0x03, lambda: self.ifg2, lambda v: setattr(self, 'ifg2', v))
        mem.reg8(0x61, lambda: self.ctl1, lambda v: setattr(self, 'ctl1', v))
        mem.reg8(0x62, lambda: self.br & 0xFF, lambda v: setattr(self, 'br', self.br & 0xFF00 | v))
        mem.reg8(0x63, lambda: self.br >> 8, lambda v: setattr(self, 'br', self.br & 0xFF | v << 8))
        mem.reg8(0x66, self._rx, lambda v: None, lambda: self.rxbuf)
        mem.reg8(0x67, lambda: self.txbuf, self._tx)
        self.reset()

    def reset(self):
        self.ie2, self.ifg2, self.ctl1, self.br, self.rxbuf, self.txbuf, self.tx = 0, 0x0A, 1, 0, 0, 0, 0

    def _rx(self):
        self.ifg2 &= ~1
        return self.rxbuf

    def _tx(self, v):
        if not self.ifg2 & 2:
            self.log.append('UCA0TXBUF: TXIFG=0 iken yazildi; karakter kayboldu (once TXIFG bekleyin)')
            return
        self.txbuf = v
        self.out.append(v)
        self.ifg2 &= ~2
        self.tx = max(self.br * UART_BITS, 20)

    def receive(self, v):
        self.rxbuf = v & 0xFF
        self.ifg2 |= 1

    def tick(self, n):
        if self.tx:
            self.tx -= n
            if self.tx <= 0:
                self.tx = 0
                self.ifg2 |= 2

    def next_event(self):
        return self.tx or None

    def pending(self):
        p = self.ie2 & self.ifg2
        return [v for bit, v in ((1, 0xFFEE), (2, 0xFFEC)) if p & bit]

    def ack(self, vec):
        if vec == 0xFFEC:
            self.ifg2 &= ~2


# Format I cycle tablosu: kaynak kategorisi -> (dst reg, dst PC, dst bellek)
_C1 = {0: (1, 2, 4), 1: (2, 2, 5), 2: (2, 3, 5), 3: (2, 3, 5), 4: (3, 3, 6)}
# Format II: (R, @, @+, #, X)
_C2 = {'sh': (1, 3, 3, 3, 4), 'push': (3, 4, 4, 4, 5), 'call': (4, 4, 5, 5, 5)}


class MSP430:
    def __init__(self):
        self.log = []
        self.mem = Mem(self.log)
        m = self.mem
        self.p1 = Port(m, 0x20, 0xFFE4, ext=0x08)   # P1.3: LaunchPad S1 butonu (G2ET), harici 47k pull-up
        self.p2 = Port(m, 0x28, 0xFFE6)
        self.ta = TimerA(m)
        self.wdt = WDT(m, self)
        self.uart = UART(m)
        self.plain = Plain(m)
        self.periphs = [self.p1, self.p2, self.ta, self.wdt, self.uart, self.plain]
        self.image = {}
        self.r = [0] * 16
        self.cycles = self.icount = 0
        self.stop = None
        self.puc_req = None
        self.reset()

    # --- yukleme / reset ---
    def load(self, image):
        self.image = dict(image)
        self.reset()

    def reset(self):
        b = self.mem.b
        b[:] = bytes(0x10000)
        b[0x1000:0x1100] = b'\xFF' * 0x100
        b[0x10FE], b[0x10FF] = 0x90, 0x86          # tipik 1 MHz kalibrasyon degerleri
        b[0xC000:] = b'\xFF' * 0x4000
        for a, d in self.image.items():
            b[a:a + len(d)] = d
        self.cycles = self.icount = 0
        self.log.clear()
        self.mem.warned.clear()
        self.uart.out.clear()
        self._puc()

    def _puc(self):
        self.puc_req = self.stop = None
        self.r = [0] * 16
        for p in self.periphs:
            p.reset()
        self.r[0] = self.mem.rw(RESET_VEC) & 0xFFFE

    def peek(self, a):
        return self.mem.rb(a & 0xFFFF, peek=True)

    # --- zaman ---
    def tick(self, n):
        self.cycles += n
        for p in (self.ta, self.wdt, self.uart):
            p.tick(n)

    # --- operand erisimi: (tur, deger) tur 0=sabit 1=register 2=bellek ---
    def _fetch(self):
        r = self.r
        w = self.mem.rw(r[0])
        r[0] = (r[0] + 2) & 0xFFFF
        return w

    def _loc(self, reg, mode, bw, dst=False):
        r = self.r
        if not dst:
            if reg == 3:
                return 0, (0, 1, 2, -1)[mode]
            if reg == 2 and mode > 1:
                return 0, (4, 8)[mode - 2]
        if mode == 0:
            return 1, reg
        if mode == 1:
            if reg == 3:
                return 2, r[3]
            a = r[0]
            ext = self._fetch()
            ea = ext if reg == 2 else ext + (a if reg == 0 else r[reg])
            return 2, ea & 0xFFFF
        if mode == 2:
            return 2, r[reg]
        if reg == 0:
            return 0, self._fetch()
        ea = r[reg]
        r[reg] = (ea + (1 if bw and reg > 1 else 2)) & 0xFFFF
        return 2, ea

    def _get(self, k, v, bw):
        if k == 2:
            return self.mem.rb(v) if bw else self.mem.rw(v)
        return (v if k == 0 else self.r[v]) & (0xFF if bw else 0xFFFF)

    def _put(self, k, v, val, bw):
        if k == 1:
            self.r[v] = val & (0xFFFE if v == 0 else 0xFFFF) & (0xFF if bw else 0xFFFF)
        elif k == 2:
            (self.mem.wb if bw else self.mem.ww)(v, val)

    @staticmethod
    def _cat(reg, mode):
        if mode == 0 or reg == 3 or (reg == 2 and mode > 1):
            return 0
        if mode == 1:
            return 4
        if mode == 2:
            return 1
        return 3 if reg == 0 else 2

    def _flags(self, c, z, n, v=None):
        r = self.r
        sr = r[2] & ~0x07 | (1 if c else 0) | (2 if z else 0) | (4 if n else 0)
        if v is not None:
            sr = sr & ~0x100 | (0x100 if v else 0)
        r[2] = sr

    # --- komutlar ---
    def _alu(self, op, s, d, bw):
        sr = self.r[2]
        m, msb = (0xFF, 0x80) if bw else (0xFFFF, 0x8000)
        if op == 4:
            return s
        if op == 0xC:
            return d & ~s & m
        if op == 0xD:
            return d | s
        if 5 <= op <= 9:
            if op <= 6:
                a, cin = s, (sr & 1 if op == 6 else 0)
            else:
                a, cin = ~s & m, (sr & 1 if op == 7 else 1)
            t = a + d + cin
            res = t & m
            self._flags(t > m, res == 0, res & msb, bool(~(a ^ d) & (a ^ res) & msb))
            return None if op == 9 else res
        if op == 0xA:                                   # DADD
            res, carry = 0, sr & 1
            for i in range(0, 8 if bw else 16, 4):
                dg = (s >> i & 15) + (d >> i & 15) + carry
                carry = 1 if dg > 9 else 0
                res |= (dg - 10 if carry else dg) << i
            self._flags(carry, res == 0, res & msb)
            return res
        res = s ^ d if op == 0xE else s & d             # XOR / BIT / AND
        z = res == 0
        self._flags(not z, z, res & msb, bool(s & d & msb) if op == 0xE else False)
        return None if op == 0xB else res

    def _fmt1(self, w, op):
        bw, ad, as_ = w >> 6 & 1, w >> 7 & 1, w >> 4 & 3
        src, dst = w >> 8 & 15, w & 15
        cat = self._cat(src, as_)
        sk, sv = self._loc(src, as_, bw)
        s = self._get(sk, sv, bw)
        dk, dv = self._loc(dst, ad, bw, dst=True)
        d = 0 if op == 4 else self._get(dk, dv, bw)
        res = self._alu(op, s, d, bw)
        if res is not None:
            self._put(dk, dv, res, bw)
        return _C1[cat][2 if ad else (1 if dst == 0 else 0)]

    def _push(self, v):
        r = self.r
        r[1] = (r[1] - 2) & 0xFFFF
        self.mem.ww(r[1], v)

    def _pop(self):
        r = self.r
        v = self.mem.rw(r[1])
        r[1] = (r[1] + 2) & 0xFFFF
        return v

    def _fmt2(self, w):
        r = self.r
        opc, bw, as_, reg = w >> 7 & 7, w >> 6 & 1, w >> 4 & 3, w & 15
        if opc == 7:
            return None
        if opc == 6:                                    # RETI
            r[2] = self._pop()
            r[0] = self._pop() & 0xFFFE
            return 5
        cat = self._cat(reg, as_)
        k, v = self._loc(reg, as_, bw)
        x = self._get(k, v, bw)
        if opc == 4:                                    # PUSH
            self._push(x)
            return _C2['push'][cat]
        if opc == 5:                                    # CALL
            self._push(r[0])
            r[0] = x & 0xFFFE
            return _C2['call'][cat]
        m, msb = (0xFF, 0x80) if bw else (0xFFFF, 0x8000)
        if opc == 1:                                    # SWPB
            res = (x & 0xFF) << 8 | x >> 8
        elif opc == 3:                                  # SXT
            res = (x & 0xFF) | (0xFF00 if x & 0x80 else 0)
            self._flags(res != 0, res == 0, res & 0x8000, False)
        else:                                           # RRC / RRA
            top = (r[2] & 1) * msb if opc == 0 else x & msb
            res = x >> 1 | top
            self._flags(x & 1, res == 0, res & msb, False)
        self._put(k, v, res, bw)
        return _C2['sh'][min(cat, 4)]

    def _jump(self, w):
        r = self.r
        sr = r[2]
        c, z, n, v = sr & 1, sr & 2, sr & 4, sr & 0x100
        off = w & 0x3FF
        off -= 0x400 if off & 0x200 else 0
        if (not z, z, not c, c, n, bool(n) == bool(v), bool(n) != bool(v), True)[w >> 10 & 7]:
            r[0] = (r[0] + 2 * off) & 0xFFFF
        return 2

    def _irq(self):
        best, owner = 0, None
        for p in self.periphs:
            for v in p.pending():
                if v > best:
                    best, owner = v, p
        if not best:
            return False
        r = self.r
        self._push(r[0])
        self._push(r[2])
        r[2] = 0
        r[0] = self.mem.rw(best) & 0xFFFE
        owner.ack(best)
        self.tick(6)
        return True

    def step(self, limit=None):
        """Tek komut (veya kesme girisi / uyku ilerletmesi). self.stop dolarsa durma nedeni."""
        if self.puc_req:
            self.log.append('PUC: ' + self.puc_req)
            self._puc()
            return
        r = self.r
        if r[2] & GIE and self._irq():
            self.icount += 1
            return
        if r[2] & CPUOFF:
            if not r[2] & GIE:
                self.stop = 'dead'
                return
            ev = [e for e in (p.next_event() for p in self.periphs) if e is not None]
            if not ev:
                self.stop = 'sleep'
                return
            n = min(ev)
            if limit is not None:
                n = min(n, limit - self.cycles)
            self.tick(max(n, 1))
            return
        pc = r[0]
        w = self.mem.rw(pc)
        if w == 0x3FFF and not r[2] & GIE:             # jmp $
            self.stop = 'halt'
            return
        if w == 0xFFFF and pc >= 0xC000:                # silinmis flash: program sonuna tasti
            self.stop = 'end'
            return
        r[0] = (pc + 2) & 0xFFFF
        top = w >> 12
        cyc = self._fmt1(w, top) if top >= 4 else self._fmt2(w) if top == 1 else \
            self._jump(w) if top in (2, 3) else None
        if cyc is None:
            r[0] = pc
            self.stop = 'illegal'
            self.log.append(f'Gecersiz komut 0x{w:04X} @ 0x{pc:04X}')
            return
        self.icount += 1
        self.tick(cyc)

    def run(self, max_cycles, breaks=()):
        """Neden doner: budget | break | halt | sleep | dead | illegal | end"""
        end = self.cycles + max_cycles
        self.stop = None
        first = True
        while self.cycles < end:
            if not first and self.r[0] in breaks and not self.r[2] & CPUOFF:
                return 'break'
            first = False
            self.step(end)
            if self.stop:
                return self.stop
        return 'budget'
