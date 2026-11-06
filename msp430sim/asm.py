"""Iki gecisli MSP430 assembler (TI/CCS sozdizimine yakin). assemble(text) -> Result."""
import ast
import difflib
import re
from dataclasses import dataclass, field

from .cpu import SYMBOLS

FMT1 = dict(mov=4, add=5, addc=6, subc=7, sub=8, cmp=9, dadd=0xA, bit=0xB, bic=0xC, bis=0xD, xor=0xE, and_=0xF)
FMT1['and'] = FMT1.pop('and_')
FMT2 = dict(rrc=0, swpb=1, rra=2, sxt=3, push=4, call=5, reti=6)
JUMPS = dict(jne=0, jnz=0, jeq=1, jz=1, jnc=2, jlo=2, jc=3, jhs=3, jn=4, jge=5, jl=6, jmp=7)
EMU = dict(
    nop=('mov', ['r3', 'r3']), ret=('mov', ['@sp+', 'pc']), pop=('mov', ['@sp+', '{0}']),
    br=('mov', ['{0}', 'pc']), clr=('mov', ['#0', '{0}']), inc=('add', ['#1', '{0}']),
    incd=('add', ['#2', '{0}']), dec=('sub', ['#1', '{0}']), decd=('sub', ['#2', '{0}']),
    tst=('cmp', ['#0', '{0}']), inv=('xor', ['#-1', '{0}']), rla=('add', ['{0}', '{0}']),
    rlc=('addc', ['{0}', '{0}']), adc=('addc', ['#0', '{0}']), sbc=('subc', ['#0', '{0}']),
    dadc=('dadd', ['#0', '{0}']), clrc=('bic', ['#1', 'sr']), setc=('bis', ['#1', 'sr']),
    clrz=('bic', ['#2', 'sr']), setz=('bis', ['#2', 'sr']), clrn=('bic', ['#4', 'sr']),
    setn=('bis', ['#4', 'sr']), eint=('bis', ['#8', 'sr']), dint=('bic', ['#8', 'sr']))
DIRECTIVES = {'.org', '.word', '.byte', '.ascii', '.asciz', '.string', '.space', '.skip', '.align',
              '.equ', '.set', '.text', '.data', '.bss', '.global', '.globl', '.sect', '.short', '.cdecls',
              '.def', '.retain', '.retainrefs'}
CG = {0: (3, 0), 1: (3, 1), 2: (3, 2), 4: (2, 2), 8: (2, 3), -1: (3, 3)}
TOKEN = re.compile(r"\s*(0[xX][0-9a-fA-F]+|\d[0-9a-fA-F]*[hH]\b|0[bB][01]+|[01]+[bB]\b|\d+|%[01]+|'(?:\\.|[^'])'|[A-Za-z_.][\w.$]*|\$|<<|>>|[-+*/&|^~()%])")
REGNAME = {'pc': 0, 'sp': 1, 'sr': 2, 'cg': 3}


class AsmError(Exception):
    pass


@dataclass
class Result:
    image: dict = field(default_factory=dict)      # addr -> bytes (bitisik bloklar)
    listing: list = field(default_factory=list)    # (addr, bytes, satir_no, kaynak)
    symbols: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)     # (satir_no, mesaj)
    warnings: list = field(default_factory=list)   # (satir_no, mesaj)


def _reg(s):
    s = s.strip().lower()
    if s in REGNAME:
        return REGNAME[s]
    m = re.fullmatch(r'r(\d+)', s)
    return int(m[1]) if m and int(m[1]) < 16 else None


def _split(s):
    """Virgulle ayir (tirnak ve parantez icindekileri koruyarak)."""
    out, cur, depth, q = [], '', 0, None
    for ch in s:
        if q:
            cur += ch
            q = None if ch == q else q
        elif ch in '"\'':
            q = ch
            cur += ch
        elif ch == ',' and depth == 0:
            out.append(cur.strip())
            cur = ''
        else:
            depth += (ch == '(') - (ch == ')')
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def _strip_comment(line):
    q = None
    for i, ch in enumerate(line):
        if q:
            q = None if ch == q else q
        elif ch in '"\'':
            q = ch
        elif ch == ';' or line.startswith('//', i):
            return line[:i]
    return line


class Asm:
    def __init__(self):
        self.res = Result()
        self.syms = {}
        self.unres = False
        self.final = False
        self.owner = {}

    # --- ifade ---
    def ev(self, s, pc):
        self.unres = False
        out, pos, s = [], 0, s.strip()
        if not s:
            raise AsmError('bos ifade')
        while pos < len(s):
            m = TOKEN.match(s, pos)
            if not m:
                raise AsmError(f'gecersiz ifade: {s!r}')
            t, pos = m[1], m.end()
            if t[0] == '%' and len(t) > 1:                     # %101 ikilik, ama 7%10 modulo
                if out and (out[-1][-1:].isdigit() or out[-1] == ')'):
                    out += ['%', str(int(t[1:]))]
                else:
                    out.append(str(int(t[1:], 2)))
            elif t[0].isdigit():
                tl = t.lower()
                if tl.endswith('h') and not tl.startswith('0x'):
                    out.append(str(int(t[:-1], 16)))
                elif tl.startswith('0x'):
                    out.append(str(int(t, 16)))
                elif tl.startswith('0b') and len(t) > 2:
                    out.append(str(int(t[2:], 2)))
                elif tl.endswith('b'):
                    out.append(str(int(t[:-1], 2)))
                else:
                    out.append(str(int(t)))
            elif t[0] == "'":
                out.append(str(ord(ast.literal_eval(t))))
            elif t == '$':
                out.append(str(pc))
            elif t[0].isalpha() or t[0] in '_.':
                if t in self.syms:
                    out.append(str(self.syms[t]))
                elif self.final:
                    raise AsmError(f'tanimsiz sembol: {t}')
                else:
                    self.unres = True
                    out.append('0')
            else:
                out.append('//' if t == '/' else t)
        if s[pos:].strip():
            raise AsmError(f'gecersiz ifade: {s!r}')
        try:
            return int(eval(' '.join(out), {'__builtins__': {}}))
        except (SyntaxError, ZeroDivisionError, TypeError, ValueError, OverflowError, MemoryError) as e:
            raise AsmError(f'ifade hesaplanamadi: {s!r} ({e})')

    def warn(self, st, msg):
        if self.final:
            self.res.warnings.append((st['no'], msg))

    @staticmethod
    def known(w):
        w = w.lower().removesuffix('.b').removesuffix('.w')
        return w in FMT1 or w in FMT2 or w in JUMPS or w in EMU

    @staticmethod
    def suggest(w, cutoff=0.6):
        names = [*FMT1, *FMT2, *JUMPS, *EMU]
        m = difflib.get_close_matches(w.lower().removesuffix('.b').removesuffix('.w'), names, 1, cutoff)
        return f' ({m[0]} mi?)' if m else ''

    # --- operandlar ---
    def parse_op(self, s):
        s = s.strip()
        if (r := _reg(s)) is not None:
            return ('r', r)
        if s.startswith('@'):
            m = re.fullmatch(r'@\s*(\w+)\s*(\+?)', s)
            if m and (r := _reg(m[1])) is not None:
                return ('@+' if m[2] else '@', r)
            raise AsmError(f'gecersiz operand: {s}')
        if s.startswith('#'):
            return ('#', s[1:])
        if s.startswith('&'):
            return ('&', s[1:])
        m = re.fullmatch(r'(.+)\(\s*(\w+)\s*\)', s)
        if m and (r := _reg(m[2])) is not None:
            return ('x', r, m[1])
        return ('sym', s)

    def enc_op(self, st, idx, op, pc_ext, bw, dst, pc, push=False):
        k = op[0]
        if k == 'r':
            return op[1], 0, None
        if k == 'x' and op[1] == 3:
            if self.ev(op[2], pc):
                raise AsmError('R3 indeksli adreslemede sifir disi ofset kullanilamaz')
            return 3, 1, None
        if dst:
            if k == 'x':
                return op[1], 1, self.ev(op[2], pc) & 0xFFFF
            if k == '&':
                return 2, 1, self.ev(op[1], pc) & 0xFFFF
            if k == 'sym':
                return 0, 1, (self.ev(op[1], pc) - pc_ext) & 0xFFFF
            raise AsmError('gecersiz hedef operand (hedefte @Rn, @Rn+ ve #imm kullanilamaz)')
        if k == '@':
            return op[1], 2, None
        if k == '@+':
            return op[1], 3, None
        if k == '#':
            v = self.ev(op[1], pc)
            if not self.final:
                st['nocg'][idx] = self.unres
            if not st['nocg'][idx]:
                key = -1 if v == -1 or v == 0xFFFF and not bw or bw and v == 0xFF else v
                if key in CG and not (push and key in (4, 8)):
                    reg, mode = CG[key]
                    return reg, mode, None
            if self.final and not (-128 if bw else -32768) <= v <= (255 if bw else 65535):
                self.warn(st, f'#{v} {"8" if bw else "16"} bite sigmiyor, kirpildi')
            return 0, 3, v & 0xFFFF
        if k == '&':
            return 2, 1, self.ev(op[1], pc) & 0xFFFF
        if k == 'x':
            return op[1], 1, self.ev(op[2], pc) & 0xFFFF
        return 0, 1, (self.ev(op[1], pc) - pc_ext) & 0xFFFF       # sym: PC-goreli

    def enc_insn(self, st, pc):
        name, args = st['op'], list(st['args'])
        bw = 0
        if name.endswith(('.b', '.w')):
            base = name[:-2]
            if (base in JUMPS or base in ('br', 'call', 'reti')
                    or base in EMU and all('{0}' not in t for t in EMU[base][1])):
                raise AsmError(f'{name}: boyut eki kullanilamaz')
        if name.endswith('.b'):
            name, bw = name[:-2], 1
        elif name.endswith('.w'):
            name = name[:-2]
        if name in EMU:
            real, tpl = EMU[name]
            need = 1 if any('{0}' in t for t in tpl) else 0
            if len(args) != need:
                raise AsmError(f'{name}: {need} operand gerekli')
            name, args = real, [t.format(args[0]) if need else t for t in tpl]
        if name in FMT1:
            if len(args) != 2:
                raise AsmError(f'{name}: 2 operand gerekli')
            sreg, sas, sext = self.enc_op(st, 0, self.parse_op(args[0]), pc + 2, bw, False, pc)
            dpc = pc + 2 + (2 if sext is not None else 0)
            dreg, dad, dext = self.enc_op(st, 1, self.parse_op(args[1]), dpc, bw, True, pc)
            w = FMT1[name] << 12 | sreg << 8 | dad << 7 | bw << 6 | sas << 4 | dreg
            return [w] + [e for e in (sext, dext) if e is not None]
        if name in FMT2:
            if name == 'reti':
                if args:
                    raise AsmError('reti operand almaz')
                return [0x1300]
            if len(args) != 1:
                raise AsmError(f'{name}: 1 operand gerekli')
            if bw and name in ('swpb', 'sxt', 'call'):
                raise AsmError(f'{name}.b yok')
            operand = self.parse_op(args[0])
            if name in ('rrc', 'rra', 'swpb', 'sxt') and operand[0] == '#':
                raise AsmError(f'{name}: hedefte #imm kullanilamaz')
            reg, as_, ext = self.enc_op(st, 0, operand, pc + 2, bw, False, pc, push=name == 'push')
            w = 0x1000 | FMT2[name] << 7 | bw << 6 | as_ << 4 | reg
            return [w] + ([ext] if ext is not None else [])
        if name in JUMPS:
            if len(args) != 1:
                raise AsmError(f'{name}: 1 operand gerekli')
            off = self.ev(args[0], pc) - (pc + 2)
            if self.final:
                if off & 1:
                    raise AsmError('jump hedefi tek adreste')
                if not -1024 <= off <= 1022:
                    raise AsmError(f'jump menzil disi ({off} byte); br #hedef kullanin')
            return [0x2000 | JUMPS[name] << 10 | (off >> 1) & 0x3FF]
        raise AsmError(f'bilinmeyen komut: {st["op"]}{self.suggest(st["op"])}')

    # --- satir ayristirma ---
    def parse(self, text):
        stmts = []
        for no, raw in enumerate(text.splitlines(), 1):
            line = _strip_comment(raw).rstrip()
            labels = []
            while True:
                m = re.match(r'\s*([A-Za-z_][\w$]*):\s*', line)
                if not m:
                    break
                labels.append(m[1])
                line = line[m.end():]
            if line and not line[0].isspace():              # sutun 0'da iki nokta olmayan etiket / "NAME .equ x"
                m = re.match(r'([A-Za-z_][\w$]*)(\s+|$)', line)
                if m and m[1].lower() not in DIRECTIVES and not self.known(m[1]):
                    rest = line[m.end():].strip()
                    w2 = rest.split(None, 1)[0].lower() if rest else ''
                    if not rest:
                        if self.suggest(m[1], 0.75):
                            self.res.warnings.append((no, f"'{m[1]}' etiket sayildi, komut mu?{self.suggest(m[1], 0.75)}"))
                        labels.append(m[1])
                        line = ''
                    elif self.known(w2) or w2 in DIRECTIVES:
                        labels.append(m[1])
                        line = rest                          # aksi halde m[1] bilinmeyen komut olarak hata verir
            line = line.strip()
            if not line:
                if labels:
                    stmts.append(dict(no=no, text=raw, labels=labels, op=None))
                continue
            parts = line.split(None, 1)
            op = parts[0].lower()
            args = _split(parts[1]) if len(parts) > 1 else []
            stmts.append(dict(no=no, text=raw, labels=labels, op=op, args=args, nocg=[False, False]))
        # "NAME .equ expr" -> ".equ NAME, expr"
        for st in stmts:
            if st['op'] in ('.equ', '.set') and len(st['args']) == 1 and st['labels']:
                st['args'] = [st['labels'].pop(), st['args'][0]]
        return stmts

    # --- gecis ---
    def emit(self, addr, data, st):
        for i, b in enumerate(data):
            a = addr + i
            if a > 0xFFFF:
                raise AsmError('adres 0xFFFF disina tasti')
            if a in self.owner:
                raise AsmError(f'0x{a:04X} adresi satir {self.owner[a]} ile cakisiyor')
            self.owner[a] = st['no']
            self.mem[a] = b
        self.res.listing.append((addr, bytes(data), st['no'], st['text'].strip()))

    def range_warn(self, st, vals, lo, hi, bits):
        for v in vals:
            if not lo <= v <= hi:
                self.warn(st, f'{v} {bits} bite sigmiyor, kirpildi')

    def define(self, name, val, no):
        if not self.final:
            if name in self.defined:
                raise AsmError(f'etiket tekrar tanimli: {name} (ilk: satir {self.defined[name]})')
            self.defined[name] = no
        self.syms[name] = val

    def strings(self, args):
        out = bytearray()
        for a in args:
            if a[:1] == '"':
                try:
                    out += ast.literal_eval(a).encode()
                except (SyntaxError, ValueError):
                    raise AsmError(f'gecersiz metin: {a}')
            else:
                raise AsmError('metin "..." icinde olmali')
        return bytes(out)

    @staticmethod
    def SECTION_BASE(sec, pc):
        if sec == '.reset':
            return 0xFFFE
        m = re.fullmatch(r'\.int(\d\d)', sec)
        return 0xFFE0 + 2 * int(m[1]) if m else pc        # .stack vb.: konumu degistirme

    def one_pass(self, stmts):
        pc, sec, secs = 0xC000, '.text', {'.text': 0xC000}
        for st in stmts:
            try:
                op = st['op']
                evenop = op is not None and (op in ('.word', '.short') or not op.startswith('.'))
                if evenop and pc & 1:
                    pc += 1
                for lab in st['labels']:
                    self.define(lab, pc, st['no'])
                if op is None:
                    continue
                args = st['args']
                if op in ('.text', '.sect'):               # CCS bolumleri: .text, ".reset", ".intNN"
                    secs[sec], sec = pc, (args[0].strip('"') if op == '.sect' and args else '.text')
                    pc = secs.get(sec, self.SECTION_BASE(sec, pc))
                    continue
                if op in ('.data', '.bss', '.global', '.globl', '.cdecls', '.def', '.retain', '.retainrefs'):
                    continue
                if op == '.org':
                    pc = self.ev(args[0], pc) & 0xFFFF
                elif op in ('.equ', '.set'):
                    if len(args) != 2:
                        raise AsmError('.equ ad, ifade')
                    self.define(args[0], self.ev(args[1], pc), st['no'])
                elif op in ('.word', '.short'):
                    vals = [self.ev(a, pc) for a in args]
                    self.range_warn(st, vals, -32768, 65535, '16')
                    data = b''.join((v & 0xFFFF).to_bytes(2, 'little') for v in vals)
                elif op == '.byte':
                    data = b''
                    for a in args:
                        if a[:1] == '"':
                            data += self.strings([a])
                        else:
                            v = self.ev(a, pc)
                            self.range_warn(st, [v], -128, 255, '8')
                            data += bytes([v & 0xFF])
                elif op in ('.ascii', '.asciz', '.string'):
                    data = self.strings(args) + (b'\0' if op != '.ascii' else b'')
                elif op in ('.space', '.skip'):
                    n = self.ev(args[0], pc)
                    if not 0 <= n <= 0x10000:
                        raise AsmError(f'{op}: gecersiz boyut {n}')
                    data = bytes([self.ev(args[1], pc) & 0xFF if len(args) > 1 else 0]) * n
                elif op == '.align':
                    n = self.ev(args[0], pc) if args else 2
                    data = bytes(-pc % max(n, 1))
                else:
                    data = b''.join(w.to_bytes(2, 'little') for w in self.enc_insn(st, pc))
                if op not in ('.org', '.equ', '.set'):
                    if self.final and data:
                        self.emit(pc, data, st)
                    pc += len(data)
            except AsmError as e:
                self.res.errors.append((st['no'], str(e)))
            except IndexError:
                self.res.errors.append((st['no'], f'{st["op"]}: eksik operand'))
            except Exception as e:                             # assembler cokmesin: satir hatasi olarak bildir
                self.res.errors.append((st['no'], f'{st["op"]}: {type(e).__name__}: {e}'))

    def run(self, text):
        stmts = self.parse(text)
        self.syms, self.defined, self.mem = dict(SYMBOLS), {}, {}
        self.one_pass(stmts)
        if not self.res.errors:
            self.final = True
            self.one_pass(stmts)
        r = self.res
        if not r.errors:
            if 0xFFFE not in self.mem:
                for n in ('start', 'main', '_start', 'RESET'):
                    if n in self.defined:
                        self.mem[0xFFFE], self.mem[0xFFFF] = self.syms[n] & 0xFF, self.syms[n] >> 8
                        break
            runs, prev = [], None
            for a in sorted(self.mem):
                if prev is not None and a == prev + 1:
                    runs[-1][1].append(self.mem[a])
                else:
                    runs.append((a, bytearray([self.mem[a]])))
                prev = a
            r.image = {a: bytes(d) for a, d in runs}
        r.symbols = {k: v for k, v in self.syms.items() if k in self.defined or k not in SYMBOLS}
        r.errors.sort()
        return r


def assemble(text):
    return Asm().run(text)
