"""Tkinter arayuzu (MARS tarzi): Edit / Execute sekmeleri, register + bellek panelleri, I/O, Console."""
import collections
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .asm import assemble
from . import ref
from .cpu import CPUOFF, GIE, MSP430, SYMBOLS

EXAMPLES = Path(__file__).parent / 'examples'
SPEEDS = {'1 kHz': 1e3, '10 kHz': 1e4, '100 kHz': 1e5, '1 MHz (gercek zaman)': 1e6, 'Max': None}
REGIONS = {'RAM 0200': 0x0200, 'Cevre birimleri 0000': 0x0000, 'Info flash 1000': 0x1000,
           'Flash C000': 0xC000, 'Vektorler FE00': 0xFE00, 'Stack (SP)': None}
REGNAMES = ['PC', 'SP', 'SR', 'CG'] + [f'R{i}' for i in range(4, 16)]
STOP_MSG = {'break': 'Breakpoint', 'halt': 'Program bitti (jmp $, kesme kapali)',
            'dead': 'CPU kapali ve GIE=0: uyanamaz (Reset gerekli)', 'illegal': 'Gecersiz komut',
            'end': 'Program sonu: kodun bittigi yerden sonrasi bos flash. Sona "jmp $" ekleyin',
            'sleep': 'Uyuyor (LPM): kesme/olay bekliyor'}
LED = {('P1', 0): '#e53935', ('P1', 6): '#43a047'}


class App(tk.Tk):
    def __init__(self, initial_file=None):
        super().__init__()
        self.title('MSP430 Simulator (G2553)')
        self.geometry('1280x820')
        self.cpu = MSP430()
        self.result = None
        self.running = False
        self.breaks = set()
        self.rows = {}                      # adres -> treeview iid
        self.prev_regs = list(self.cpu.r)
        self.prev_mem = (None, b'')
        self.log_seen = 0
        self.rxq = collections.deque()
        self.mem_start = 0x0200
        self.path = None
        self.dirty = False
        self._loading = False
        self.carry = 0.0
        self.last = time.perf_counter()
        self._menu()
        self._layout()
        self.bind('<F3>', lambda e: self.do_assemble())
        self.bind('<F5>', lambda e: self.do_run())
        self.bind('<F6>', lambda e: self.do_pause())
        self.bind('<F7>', lambda e: self.do_step())
        self.bind('<F8>', lambda e: self.do_reset())
        self.bind('<F1>', lambda e: self.show_help())
        self.bind('<Control-s>', lambda e: self.file_save())
        self.bind('<Control-S>', lambda e: self.file_save(True))
        self.protocol('WM_DELETE_WINDOW', lambda: self.destroy() if self._confirm_discard() else None)
        self.help_win = None
        if initial_file and Path(initial_file).is_file():
            p = Path(initial_file)
            self.path = str(p.resolve())
            self.set_text(p.read_text(encoding='utf-8', errors='replace'))
            self.status.set(f'Acildi: {p.name}')
        else:
            self.load_example('main.asm')
        self.refresh()

    # ---------------- arayuz kurulumu ----------------
    def _menu(self):
        mb = tk.Menu(self)
        f = tk.Menu(mb, tearoff=0)
        f.add_command(label='Yeni', command=self.file_new)
        f.add_command(label='Ac...', command=self.file_open)
        f.add_command(label='Kaydet', command=self.file_save)
        f.add_command(label='Farkli kaydet...', command=lambda: self.file_save(True))
        f.add_separator()
        f.add_command(label='Cikis', command=self.destroy)
        mb.add_cascade(label='Dosya', menu=f)
        ex = tk.Menu(mb, tearoff=0)
        for p in sorted(EXAMPLES.glob('*.asm')):
            ex.add_command(label=p.stem, command=lambda n=p.name: self.load_example(n))
        mb.add_cascade(label='Ornekler', menu=ex)
        r = tk.Menu(mb, tearoff=0)
        for lbl, cmd, key in (('Assemble', self.do_assemble, 'F3'), ('Run', self.do_run, 'F5'),
                              ('Pause', self.do_pause, 'F6'), ('Step', self.do_step, 'F7'),
                              ('Reset', self.do_reset, 'F8')):
            r.add_command(label=lbl, command=cmd, accelerator=key)
        mb.add_cascade(label='Calistir', menu=r)
        h = tk.Menu(mb, tearoff=0)
        h.add_command(label='Komut referansi', command=self.show_help, accelerator='F1')
        mb.add_cascade(label='Yardim', menu=h)
        self.config(menu=mb)

    # ---------------- yardim penceresi (MARS "Help") ----------------
    def show_help(self):
        if self.help_win and self.help_win.winfo_exists():
            self.help_win.lift()
            self.help_win.focus_set()
            return
        w = self.help_win = tk.Toplevel(self)
        w.title('MSP430 komut referansi')
        w.geometry('900x600')
        nb = ttk.Notebook(w)
        nb.pack(fill='both', expand=True)

        def table(parent, cols, widths, rows):
            fr = ttk.Frame(parent)
            tv = ttk.Treeview(fr, columns=cols, show='headings', selectmode='browse')
            for c, wd in zip(cols, widths):
                tv.heading(c, text=c)
                tv.column(c, width=wd, anchor='w', stretch=c == cols[-1])
            sb = ttk.Scrollbar(fr, command=tv.yview)
            tv.configure(yscrollcommand=sb.set)
            sb.pack(side='right', fill='y')
            tv.pack(fill='both', expand=True)
            for r in rows:
                tv.insert('', 'end', values=r)
            return fr, tv

        def text(parent, s, height=None):
            t = tk.Text(parent, wrap='word', font='TkFixedFont', height=height or 10)
            t.insert('1.0', s)
            t.configure(state='disabled')
            return t

        # komutlar: grup filtresi + arama + ayrinti
        fr = ttk.Frame(nb)
        nb.add(fr, text='Komutlar')
        top = ttk.Frame(fr, padding=4)
        top.pack(fill='x')
        groups = ['Tumu'] + list(dict.fromkeys(r[2] for r in ref.INSNS))
        grp = ttk.Combobox(top, values=groups, state='readonly', width=12)
        grp.set('Tumu')
        grp.pack(side='left')
        ttk.Label(top, text='  Ara:').pack(side='left')
        q = tk.StringVar()
        ttk.Entry(top, textvariable=q, width=20).pack(side='left')
        ttk.Label(top, text='   Bayraklar: C Z N V   * etkilenir  0 silinir  - degismez  U tanimsiz').pack(side='left')
        cols = ('Komut', 'Sozdizimi', 'Grup', 'Islem', 'C Z N V')
        tbl, tv = table(fr, cols, (90, 150, 80, 190, 80), [])
        tbl.pack(fill='both', expand=True)
        det = tk.Text(fr, wrap='word', font='TkFixedFont', height=7, state='disabled')
        det.pack(fill='x')

        def fill(*_):
            tv.delete(*tv.get_children())
            s = q.get().lower()
            for r in ref.INSNS:
                if grp.get() in ('Tumu', r[2]) and s in ' '.join(r).lower():
                    tv.insert('', 'end', values=r[:5], tags=(str(ref.INSNS.index(r)),))

        def pick(_=None):
            sel = tv.selection()
            if not sel:
                return
            r = ref.INSNS[int(tv.item(sel[0], 'tags')[0])]
            det.configure(state='normal')
            det.delete('1.0', 'end')
            det.insert('1.0', f'{r[1]}\nIslem   : {r[3]}\nBayrak  : {r[4]}   (C Z N V)\n\n{r[5]}')
            det.configure(state='disabled')
        q.trace_add('write', fill)
        grp.bind('<<ComboboxSelected>>', fill)
        tv.bind('<<TreeviewSelect>>', pick)
        fill()

        f, _ = table(nb, ('Mod', 'Sozdizimi', 'Anlami', 'Ornek', 'Kullanim'), (150, 120, 300, 130, 90), ref.ADDRESSING)
        nb.add(f, text='Adresleme')
        f, _ = table(nb, ('Direktif', 'Aciklama', 'Ornek'), (200, 450, 220),
                     [(a, b, c.replace('\n', ' / ')) for a, b, c in ref.DIRECTIVES])
        nb.add(f, text='Direktifler')
        fr = ttk.Frame(nb)
        nb.add(fr, text='Cycle')
        text(fr, ref.CYCLES, 30).pack(fill='both', expand=True)
        fr = ttk.Frame(nb)
        nb.add(fr, text='Kesmeler')
        f, _ = table(fr, ('Vektor', 'Adres', 'Kaynak', 'Bayrak silme'), (110, 80, 220, 300), ref.INTERRUPTS)
        f.pack(fill='x')
        text(fr, ref.NOTES, 12).pack(fill='both', expand=True)

        fr = ttk.Frame(nb)
        nb.add(fr, text='Semboller')
        top = ttk.Frame(fr, padding=4)
        top.pack(fill='x')
        ttk.Label(top, text='Ara:').pack(side='left')
        sq = tk.StringVar()
        ttk.Entry(top, textvariable=sq, width=24).pack(side='left')
        ttk.Label(top, text='   Onceden tanimli (msp430.h gibi), .include gerekmez').pack(side='left')
        sf, st = table(fr, ('Sembol', 'Deger'), (260, 120), [])
        sf.pack(fill='both', expand=True)

        def sfill(*_):
            st.delete(*st.get_children())
            for k, v in sorted(SYMBOLS.items()):
                if sq.get().lower() in k.lower():
                    st.insert('', 'end', values=(k, f'0x{v:04X}  ({v})'))
        sq.trace_add('write', sfill)
        sfill()

    def _layout(self):
        bar = ttk.Frame(self, padding=4)
        bar.pack(fill='x')
        for t, c in (('Assemble F3', self.do_assemble), ('Run F5', self.do_run), ('Step F7', self.do_step),
                     ('Pause F6', self.do_pause), ('Reset F8', self.do_reset)):
            ttk.Button(bar, text=t, command=c).pack(side='left', padx=2)
        ttk.Label(bar, text='  Hiz:').pack(side='left')
        self.speed = ttk.Combobox(bar, values=list(SPEEDS), state='readonly', width=20)
        self.speed.set('1 MHz (gercek zaman)')
        self.speed.pack(side='left')
        self.status = tk.StringVar(value='Hazir')
        ttk.Label(self, textvariable=self.status, relief='sunken', anchor='w').pack(side='bottom', fill='x')

        vp = ttk.PanedWindow(self, orient='vertical')
        vp.pack(fill='both', expand=True)
        hp = ttk.PanedWindow(vp, orient='horizontal')
        vp.add(hp, weight=4)
        self.nb = ttk.Notebook(hp)
        hp.add(self.nb, weight=3)
        self._edit_tab()
        self._exec_tab()
        right = ttk.PanedWindow(hp, orient='vertical')
        hp.add(right, weight=2)
        self._regs(right)
        self._memview(right)
        self.bottom = ttk.Notebook(vp)
        vp.add(self.bottom, weight=2)
        self._console()
        self._io()
        self._messages()

    def _edit_tab(self):
        fr = ttk.Frame(self.nb)
        self.nb.add(fr, text='Edit')
        self.gutter = tk.Text(fr, width=5, padx=4, takefocus=0, border=0, background='#eee', foreground='#555', state='disabled',
                              font='TkFixedFont')
        self.editor = tk.Text(fr, undo=True, wrap='none', font='TkFixedFont')
        sb = ttk.Scrollbar(fr, command=self._yview)
        self.editor.config(yscrollcommand=lambda a, b: (sb.set(a, b), self.gutter.yview_moveto(a)))
        self.gutter.pack(side='left', fill='y')
        sb.pack(side='right', fill='y')
        self.editor.pack(side='left', fill='both', expand=True)
        self.editor.bind('<KeyRelease>', lambda e: self._numbers(), add='+')
        self.editor.bind('<<Modified>>', lambda e: self._on_modified())
        self.editor.tag_configure('err', background='#ffcdd2')
        self.editor.tag_configure('warn', background='#fff9c4')

    def _on_modified(self):
        if self.editor.edit_modified():
            self.editor.edit_modified(False)
            if not self._loading:
                self._edited()

    def _yview(self, *a):
        self.editor.yview(*a)
        self.gutter.yview(*a)

    def _numbers(self):
        n = int(self.editor.index('end-1c').split('.')[0])
        self.gutter.config(state='normal')
        self.gutter.delete('1.0', 'end')
        self.gutter.insert('1.0', '\n'.join(str(i) for i in range(1, n + 1)))
        self.gutter.config(state='disabled')
        self.gutter.yview_moveto(self.editor.yview()[0])

    def _exec_tab(self):
        fr = ttk.Frame(self.nb)
        self.nb.add(fr, text='Execute')
        self.tree = ttk.Treeview(fr, columns=('bp', 'addr', 'code', 'src'), show='headings', selectmode='none')
        for c, t, w in (('bp', 'BP', 30), ('addr', 'Adres', 70), ('code', 'Kod', 150), ('src', 'Kaynak', 400)):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, stretch=(c == 'src'))
        sb = ttk.Scrollbar(fr, command=self.tree.yview)
        self.tree.config(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        self.tree.pack(fill='both', expand=True)
        self.tree.tag_configure('pc', background='#fff59d', foreground='black')
        self.tree.tag_configure('bp', foreground='#c62828')
        self.tree.bind('<Double-1>', self._toggle_bp)

    def _regs(self, parent):
        fr = ttk.LabelFrame(parent, text='Registers', padding=4)
        parent.add(fr, weight=1)
        self.reg_lbl = []
        for i, n in enumerate(REGNAMES):
            l = tk.Label(fr, text='', font='TkFixedFont', anchor='w', bg='#f5f5f5', fg='black')
            l.grid(row=i % 8, column=i // 8, sticky='w', padx=8)
            self.reg_lbl.append(l)
        self.flags = tk.Label(fr, font='TkFixedFont', anchor='w', bg='#f5f5f5', fg='black')
        self.flags.grid(row=8, column=0, columnspan=2, sticky='w', pady=(6, 0))
        self.stats = tk.Label(fr, font='TkFixedFont', anchor='w', justify='left', bg='#f5f5f5', fg='black')
        self.stats.grid(row=9, column=0, columnspan=2, sticky='w')

    def _memview(self, parent):
        fr = ttk.LabelFrame(parent, text='Bellek', padding=4)
        parent.add(fr, weight=3)
        top = ttk.Frame(fr)
        top.pack(fill='x')
        self.region = ttk.Combobox(top, values=list(REGIONS), state='readonly', width=20)
        self.region.set('RAM 0200')
        self.region.pack(side='left')
        self.region.bind('<<ComboboxSelected>>', self._region)
        ttk.Button(top, text='<', width=2, command=lambda: self._page(-512)).pack(side='left')
        ttk.Button(top, text='>', width=2, command=lambda: self._page(512)).pack(side='left')
        self.addr_e = ttk.Entry(top, width=7)
        self.addr_e.pack(side='left', padx=4)
        self.addr_e.bind('<Return>', self._goto)
        ttk.Label(top, text='(hex adres + Enter)').pack(side='left')
        self.mem = tk.Text(fr, font='TkFixedFont', width=70, height=20, wrap='none', state='disabled')
        self.mem.pack(fill='both', expand=True)
        self.mem.tag_configure('chg', foreground='#c62828', background='#ffe0e0')

    def _console(self):
        fr = ttk.Frame(self.bottom)
        self.bottom.add(fr, text='Console (UART)')
        self.con = tk.Text(fr, height=8, state='disabled', font='TkFixedFont', background='#111', foreground='#9f9')
        self.con.pack(fill='both', expand=True)
        row = ttk.Frame(fr)
        row.pack(fill='x')
        ttk.Label(row, text='UART RX gonder:').pack(side='left')
        self.rx_e = ttk.Entry(row)
        self.rx_e.pack(side='left', fill='x', expand=True)
        self.rx_e.bind('<Return>', self._send)
        self.nl = tk.BooleanVar()
        ttk.Checkbutton(row, text='+ \\n', variable=self.nl).pack(side='left')

    def _io(self):
        fr = ttk.Frame(self.bottom, padding=6)
        self.bottom.add(fr, text='I/O (GPIO)')
        self.pin_w = []
        for r, (name, port) in enumerate((('P1', self.cpu.p1), ('P2', self.cpu.p2))):
            ttk.Label(fr, text=name, font='TkHeadingFont').grid(row=r, column=0, padx=6)
            for b in range(8):
                cell = ttk.Frame(fr)
                cell.grid(row=r, column=8 - b, padx=6, pady=4)
                cv = tk.Canvas(cell, width=26, height=26, highlightthickness=0)
                oval = cv.create_oval(3, 3, 23, 23, fill='#555', outline='#222')
                cv.pack()
                s2 = (name, b) == ('P1', 3)
                ttk.Label(cell, text=f'{name}.{b}' + (' (S2)' if s2 else '')).pack()
                if s2:                                       # anlik buton: basilinca 0
                    btn = ttk.Button(cell, text='bas', width=5)
                    btn.bind('<ButtonPress-1>', lambda e, p=port, n=b: p.set_input(n, 0))
                    btn.bind('<ButtonRelease-1>', lambda e, p=port, n=b: p.set_input(n, 1))
                    btn.pack()
                else:
                    v = tk.BooleanVar(value=bool(port.ext >> b & 1))
                    ttk.Checkbutton(cell, variable=v,
                                    command=lambda p=port, n=b, v=v: p.set_input(n, v.get())).pack()
                mode = ttk.Label(cell, text='in', foreground='#777')
                mode.pack()
                self.pin_w.append((port, name, b, cv, oval, mode))

    def _messages(self):
        fr = ttk.Frame(self.bottom)
        self.bottom.add(fr, text='Messages')
        self.msgs = tk.Listbox(fr, height=8, font='TkFixedFont')
        self.msgs.pack(fill='both', expand=True)
        self.msgs.bind('<Double-1>', self._goto_err)
        self.msg_tab = fr

    # ---------------- dosya ----------------
    def set_text(self, s):
        self._loading = True
        self.editor.delete('1.0', 'end')
        self.editor.insert('1.0', s)
        self.editor.edit_modified(False)
        self._loading = False
        self._numbers()
        self.result = None
        self.dirty = False

    def _edited(self):
        self.result = None                 # bayat kodla calistirmayi onle
        if not self.dirty:
            self.dirty = True
            self.status.set('Kod degisti: F3 ile yeniden assemble edin')

    def _confirm_discard(self):
        """Kaydedilmemis kod varken sorar. Devam edilecekse True."""
        if not self.dirty:
            return True
        a = messagebox.askyesnocancel('Kaydedilmemis kod',
                                      'Kod kaydedilmedi. Kaydetmek ister misiniz?')
        if a is None:
            return False
        if a:
            self.file_save()
        return True

    def file_new(self):
        if self._confirm_discard():
            self.load_example('main.asm')
            self.path = None

    def file_open(self):
        if not self._confirm_discard():
            return
        p = filedialog.askopenfilename(filetypes=[('Assembly', '*.asm *.s'), ('Tum dosyalar', '*')])
        if p:
            self.path = p
            self.set_text(Path(p).read_text(encoding='utf-8', errors='replace'))
            self.status.set(f'Acildi: {p}')

    def file_save(self, as_=False):
        if as_ or not self.path:
            self.path = filedialog.asksaveasfilename(defaultextension='.asm')
        if self.path:
            Path(self.path).write_text(self.editor.get('1.0', 'end-1c'), encoding='utf-8')
            self.dirty = False
            self.status.set(f'Kaydedildi: {self.path}')

    def load_example(self, name):
        if not self._confirm_discard():
            return
        self.path = None
        self.set_text((EXAMPLES / name).read_text())
        self.status.set(f'Ornek yuklendi: {name}. F3 ile assemble edin.')

    # ---------------- assemble / kontrol ----------------
    def note(self, s):
        self.msgs.insert('end', s)
        self.msgs.see('end')

    def do_assemble(self):
        self.running = False
        res = self.result = assemble(self.editor.get('1.0', 'end-1c'))
        self.msgs.delete(0, 'end')
        self.editor.tag_remove('err', '1.0', 'end')
        self.editor.tag_remove('warn', '1.0', 'end')
        for no, m in res.errors:
            self.note(f'HATA {no}: {m}')
            self.editor.tag_add('err', f'{no}.0', f'{no}.end')
        for no, m in res.warnings:
            self.note(f'uyari {no}: {m}')
            self.editor.tag_add('warn', f'{no}.0', f'{no}.end')
        if res.errors:
            self.bottom.select(self.msg_tab)
            self.status.set(f'Assemble basarisiz: {len(res.errors)} hata')
            return False
        self.dirty = False
        self.cpu.load(res.image)
        self._reset_views()
        self.tree.delete(*self.tree.get_children())
        self.rows, self.iid_addr, self.pc_iid = {}, {}, None
        for addr, data, no, text in res.listing:
            if len(data) % 2:
                code = ' '.join(f'{b:02X}' for b in data[:8])
            else:
                code = ' '.join(f'{data[i] | data[i + 1] << 8:04X}' for i in range(0, min(len(data), 8), 2))
            code += ' ...' if len(data) > 8 else ''
            iid = self.tree.insert('', 'end', values=('●' if addr in self.breaks else '', f'{addr:04X}', code, text))
            self.rows.setdefault(addr, iid)
            self.iid_addr[iid] = addr
        for a in sorted(self.breaks):                 # yeni listing'de kod satiri yoksa breakpoint'i sil
            if a not in self.rows:
                self.breaks.discard(a)
        self.nb.select(1)
        nw = f' ({len(res.warnings)} uyari, Messages sekmesi)' if res.warnings else ''
        self.note(f'Assemble OK: {sum(len(d) for d in res.image.values())} bayt{nw}')
        self.status.set(f'Assemble OK{nw}. F5 = Run, F7 = Step')
        self.refresh()
        return True

    def _reset_views(self):
        self.rxq.clear()
        self.log_seen = 0
        self.con.config(state='normal')
        self.con.delete('1.0', 'end')
        self.con.config(state='disabled')
        self.prev_regs = list(self.cpu.r)

    def ready(self):
        if self.result is None or self.result.errors:
            if not self.do_assemble():
                return False
        if self.cpu.mem.rw(0xFFFE) == 0xFFFF:
            self.status.set('Reset vektoru yok: ".org RESET_VECTOR" + ".word start" ekleyin (veya etiketi start/main yapin)')
            return False
        return True

    def do_run(self):
        if self.running or not self.ready():
            return
        self.running = True
        self.last = time.perf_counter()
        self.status.set('Calisiyor...')
        self.tick()

    def do_pause(self):
        self.running = False
        self.status.set('Duraklatildi')

    def do_step(self):
        self.running = False
        if not self.ready():
            return
        self.cpu.stop = None
        self.feed_rx()
        self.cpu.step()
        self.refresh()
        self.status.set(STOP_MSG.get(self.cpu.stop, 'Step'))

    def do_reset(self):
        self.running = False
        self.cpu.reset()
        self._reset_views()
        self.refresh()
        self.status.set('Reset')

    def feed_rx(self):
        if self.rxq and not self.cpu.uart.ifg2 & 1:
            self.cpu.uart.receive(self.rxq.popleft())

    def _send(self, e):
        s = self.rx_e.get() + ('\n' if self.nl.get() else '')
        self.rxq.extend(s.encode('latin-1', 'replace'))
        self.rx_e.delete(0, 'end')

    def tick(self):
        if not self.running:
            return
        now = time.perf_counter()
        dt = min(now - self.last, 0.1)
        self.last = now
        self.feed_rx()
        hz = SPEEDS[self.speed.get()]
        why = 'budget'
        if hz is None:
            while why == 'budget' and time.perf_counter() - now < 0.012:
                why = self.cpu.run(3000, self.breaks)
        else:
            self.carry += hz * dt
            n, self.carry = int(self.carry), self.carry % 1
            if n:
                why = self.cpu.run(n, self.breaks)
        self.refresh()
        if why in ('break', 'halt', 'dead', 'illegal', 'end'):
            self.running = False
        self.status.set(STOP_MSG.get(why, 'Calisiyor...'))
        if self.running:
            self.after(15, self.tick)

    # ---------------- breakpoint / hata atlama ----------------
    def _toggle_bp(self, e):
        iid = self.tree.identify_row(e.y)
        if not iid:
            return
        a = self.iid_addr[iid]
        self.breaks ^= {a}
        v = list(self.tree.item(iid, 'values'))
        v[0] = '●' if a in self.breaks else ''
        self.tree.item(iid, values=v)

    def _goto_err(self, e):
        s = self.msgs.get(self.msgs.nearest(e.y))
        n = s.split(':')[0]
        if n.isdigit():
            self.nb.select(0)
            self.editor.see(f'{n}.0')
            self.editor.mark_set('insert', f'{n}.0')
            self.editor.focus_set()

    # ---------------- bellek gorunumu ----------------
    def _region(self, e=None):
        a = REGIONS[self.region.get()]
        self.follow_sp = a is None
        self.mem_start = 0x0200 if a is None else a
        self.prev_mem = (None, b'')
        self.refresh()

    def _goto(self, e):
        try:
            self.mem_start = min(int(self.addr_e.get(), 16), 0xFE00) & 0xFFF0
        except ValueError:
            return
        self.follow_sp = False
        self.prev_mem = (None, b'')
        self.refresh()

    def _page(self, d):
        self.follow_sp = False
        self.mem_start = max(0, min(0xFE00, self.mem_start + d))
        self.refresh()

    follow_sp = False

    def draw_mem(self):
        if self.follow_sp:
            self.mem_start = max(0, min(0xFE00, (self.cpu.r[1] - 0x40) & 0xFFF0))
        s = self.mem_start
        data = bytes(self.cpu.peek(a) for a in range(s, min(s + 512, 0x10000)))
        ps, pd = self.prev_mem
        if (ps, pd) == (s, data):
            return
        lines, chg = [], []
        for row in range(32):
            chunk = data[row * 16:row * 16 + 16]
            lines.append(f'{s + row * 16:04X}  ' + ' '.join(f'{b:02X}' for b in chunk) + '  ' +
                         ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk))
            if ps == s:
                chg += [(row, i) for i in range(16) if chunk[i] != pd[row * 16 + i]]
        self.mem.config(state='normal')
        self.mem.delete('1.0', 'end')
        self.mem.insert('1.0', '\n'.join(lines))
        for row, i in chg:
            self.mem.tag_add('chg', f'{row + 1}.{6 + 3 * i}', f'{row + 1}.{8 + 3 * i}')
        self.mem.config(state='disabled')
        self.prev_mem = (s, data)

    # ---------------- ekran yenileme ----------------
    def refresh(self):
        cpu, r = self.cpu, self.cpu.r
        for i, l in enumerate(self.reg_lbl):
            l.config(text=f'{REGNAMES[i]:>3}  {r[i]:04X}  {r[i]:6d}',
                     fg='#c62828' if r[i] != self.prev_regs[i] else 'black')
        self.prev_regs = list(r)
        sr = r[2]
        self.flags.config(text=f'V={sr >> 8 & 1} N={sr >> 2 & 1} Z={sr >> 1 & 1} C={sr & 1}  '
                               f'GIE={bool(sr & GIE):d} CPUOFF={bool(sr & CPUOFF):d}')
        self.stats.config(text=f'Cycles: {cpu.cycles}\nKomut:  {cpu.icount}\n'
                               f'Sure:   {cpu.cycles / 1000:.3f} ms @1 MHz')
        iid = self.rows.get(r[0]) if hasattr(self, 'rows') else None
        old = getattr(self, 'pc_iid', None)
        if old and old != iid:
            self.tree.item(old, tags=('bp',) if self.iid_addr[old] in self.breaks else ())
        if iid:
            self.tree.item(iid, tags=('pc',))
            self.tree.see(iid)
        self.pc_iid = iid
        self.draw_mem()
        for port, name, b, cv, oval, mode in self.pin_w:
            lvl, out = port.pins() >> b & 1, port.rg[2] >> b & 1
            cv.itemconfig(oval, fill=LED.get((name, b), '#fdd835') if lvl else '#555', width=3 if out else 1)
            mode.config(text='out' if out else 'in')
        if cpu.uart.out:
            self.con.config(state='normal')
            self.con.insert('end', bytes(cpu.uart.out).decode('latin-1').replace('\r', ''))
            self.con.see('end')
            self.con.config(state='disabled')
            cpu.uart.out.clear()
        for m in cpu.log[self.log_seen:]:
            self.note(m)
        self.log_seen = len(cpu.log)


def main(initial_file=None):
    App(initial_file=initial_file).mainloop()
