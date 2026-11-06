import unittest

from msp430sim.asm import assemble
from msp430sim.cpu import MSP430

HDR = '    .org 0xC000\nstart:\n    mov #WDTPW|WDTHOLD, &WDTCTL\n    mov #__STACK_END, SP\n'


def build(body, hdr=HDR):
    res = assemble(hdr + body)
    assert not res.errors, res.errors
    cpu = MSP430()
    cpu.load(res.image)
    return cpu, res


def run(body, cycles=100000, hdr=HDR):
    cpu, res = build(body + '\n    jmp $\n', hdr)
    why = cpu.run(cycles)
    return cpu, why


def words(src):
    res = assemble('.org 0xC000\n' + src)
    assert not res.errors, res.errors
    d = res.image[0xC000]
    return [d[i] | d[i + 1] << 8 for i in range(0, len(d), 2)]


class Encoding(unittest.TestCase):
    def test_vectors(self):
        cases = {'mov #0x1234, r5': [0x4035, 0x1234], 'mov.b #0, r5': [0x4345], 'nop': [0x4303],
                 'ret': [0x4130], 'reti': [0x1300], 'push r5': [0x1205], 'jmp $': [0x3FFF],
                 'call #0xC010': [0x12B0, 0xC010], 'mov &0x0021, r5': [0x4215, 0x0021],
                 'add 4(r6), r7': [0x5617, 0x0004], 'clr r5': [0x4305], 'mov #8, r5': [0x4235],
                 'mov #-1, r5': [0x4335], 'eint': [0xD232]}
        for src, exp in cases.items():
            self.assertEqual(words(src), exp, src)

    def test_push_four_eight_match_ccs(self):
        # CCS 12.8.1 / cl430 21.6.1.LTS: these PUSH immediates use an extension word.
        for src, expected in {'push #4': [0x1230, 4], 'push #8': [0x1230, 8],
                              'push.b #4': [0x1270, 4], 'push.b #8': [0x1270, 8]}.items():
            self.assertEqual(words(src), expected, src)
        self.assertEqual(words('push #2'), [0x1223])
        self.assertEqual(words('mov #4, r5'), [0x4225])

    def test_shift_immediate_destination_rejected_like_ccs(self):
        for src in ('rrc #0', 'rra #1', 'swpb #2', 'sxt #4'):
            self.assertTrue(assemble('.org 0xC000\n' + src).errors, src)
        self.assertEqual(words('push #1'), [0x1213])

    def test_byte_immediate_outside_byte_range_keeps_literal(self):
        # CCS cl430 21.6.1: byte-sized -1/255 use CG, 0xFFFF/-257 use the full literal.
        for src, expected in {'mov.b #0xFFFF, r5': [0x4075, 0xFFFF],
                              'mov.b #-257, r5': [0x4075, 0xFEFF],
                              'push.b #0xFFFF': [0x1270, 0xFFFF]}.items():
            self.assertEqual(words(src), expected, src)
        self.assertEqual(words('mov.b #255, r5'), [0x4375])

    def test_r3_indexed_offset_matches_ccs(self):
        for src, expected in {'mov 0(r3), r5': [0x4315],
                              'mov r5, 0(r3)': [0x4583],
                              'rrc 0(r3)': [0x1013]}.items():
            self.assertEqual(words(src), expected, src)
        for src in ('mov 2(r3), r5', 'mov r5, 2(r3)', 'rrc 2(r3)', 'call 2(r3)'):
            self.assertTrue(assemble('.org 0xC000\n' + src).errors, src)

    def test_br_suffix_rejected_like_ccs(self):
        for suffix in ('.b', '.w'):
            for operand in ('r5', '4(r6)', '&0x0200', '@r5', '@r5+', '#4',
                            'r3', 'sr', 'pc', 'sp'):
                src = f'br{suffix} {operand}'
                self.assertTrue(assemble('.org 0xC000\n' + src).errors, src)
        self.assertEqual(words('br r5'), [0x4500])
        self.assertEqual(words('mov.b r5, pc'), [0x4540])

    def test_jump_suffix_rejected_like_ccs(self):
        for mnemonic in ('jne', 'jnz', 'jeq', 'jz', 'jnc', 'jlo', 'jc', 'jhs',
                         'jn', 'jge', 'jl', 'jmp'):
            for suffix in ('.b', '.w'):
                src = f'{mnemonic}{suffix} $'
                with self.subTest(src=src):
                    self.assertTrue(assemble('.org 0xC000\n ' + src).errors)
        self.assertEqual(words('jmp $'), [0x3FFF])

    def test_call_reti_suffix_rejected_like_ccs(self):
        for src in ('call.b r5', 'call.w r5', 'reti.b', 'reti.w'):
            with self.subTest(src=src):
                self.assertTrue(assemble('.org 0xC000\n ' + src).errors)
        self.assertEqual(words('call r5'), [0x1285])
        self.assertEqual(words('reti'), [0x1300])

    def test_operandless_emulated_suffix_rejected_like_ccs(self):
        for mnemonic in ('nop', 'ret', 'clrc', 'setc', 'clrz', 'setz',
                         'clrn', 'setn', 'eint', 'dint'):
            for suffix in ('.b', '.w'):
                src = mnemonic + suffix
                with self.subTest(src=src):
                    self.assertTrue(assemble('.org 0xC000\n ' + src).errors)
        for src in ('nop', 'ret', 'clrc', 'setc', 'eint'):
            self.assertFalse(assemble('.org 0xC000\n ' + src).errors, src)
        for src in ('clr.b r5', 'pop.b r5', 'inc.b r5'):
            self.assertFalse(assemble('.org 0xC000\n ' + src).errors, src)

    def test_symbolic_and_jump(self):
        self.assertEqual(words('a: jne a\n'), [0x23FF])
        # symbolic: mov a, r5 (PC-goreli ofset, ext word adresi 0xC002, a=0xC000 -> -2)
        self.assertEqual(words('a: nop\n mov a, r5\n')[2], 0xFFFC)

    def test_errors(self):
        self.assertTrue(assemble('foo r1').errors)
        self.assertTrue(assemble('mov r5, @r6').errors)
        self.assertTrue(assemble('jmp x\n.org 0xD000\nx: nop').errors)   # menzil disi
        self.assertTrue(assemble('a: nop\na: nop').errors)


class Alu(unittest.TestCase):
    def sr(self, cpu):
        s = cpu.r[2]
        return dict(C=s & 1, Z=s >> 1 & 1, N=s >> 2 & 1, V=s >> 8 & 1)

    def test_add_overflow(self):
        cpu, _ = run('mov #0x7FFF, r5\n add #1, r5')
        self.assertEqual(cpu.r[5], 0x8000)
        self.assertEqual(self.sr(cpu), dict(C=0, Z=0, N=1, V=1))

    def test_add_carry(self):
        cpu, _ = run('mov #0xFFFF, r5\n add #1, r5')
        self.assertEqual((cpu.r[5], self.sr(cpu)['C'], self.sr(cpu)['Z']), (0, 1, 1))

    def test_sub_cmp(self):
        cpu, _ = run('mov #5, r5\n sub #3, r5\n mov #5, r6\n cmp #5, r6')
        self.assertEqual(cpu.r[5], 2)
        self.assertEqual((self.sr(cpu)['Z'], self.sr(cpu)['C']), (1, 1))     # esit: Z=1, borrow yok C=1
        self.assertEqual(cpu.r[6], 5)

    def test_byte_clears_high(self):
        cpu, _ = run('mov #0x1234, r5\n mov.b #0x56, r5')
        self.assertEqual(cpu.r[5], 0x56)

    def test_shifts_swpb_sxt(self):
        cpu, _ = run('mov #0x8001, r5\n rra r5\n mov #0x1234, r6\n swpb r6\n mov #0x80, r7\n sxt r7')
        self.assertEqual((cpu.r[5], cpu.r[6], cpu.r[7]), (0xC000, 0x3412, 0xFF80))
        cpu, _ = run('setc\n mov #2, r5\n rrc r5')
        self.assertEqual(cpu.r[5], 0x8001)

    def test_r3_zero_index_destination_does_not_consume_next_instruction(self):
        cpu, _ = run('mov #5, r5\n mov r5, 0(r3)\n mov #9, r6')
        self.assertEqual(cpu.r[6], 9)
        cpu, _ = run('mov #3, r5\n rrc 0(r3)\n mov #9, r6')
        self.assertEqual(cpu.r[6], 9)

    def test_dadd(self):
        cpu, _ = run('clrc\n mov #0x0199, r5\n dadd #0x0001, r5')
        self.assertEqual(cpu.r[5], 0x0200)

    def test_autoinc_byte(self):
        cpu, _ = run('mov #0x0200, r5\n mov #0x0201, r6\n mov.b @r5+, r7\n push.b r7\n pop r8')
        self.assertEqual(cpu.r[5], 0x0201)
        self.assertEqual(cpu.r[1], 0x0400)

    def test_call_ret_stack(self):
        cpu, _ = run('call #f\n mov #1, r6\n jmp end\nf: mov #7, r5\n ret\nend: nop')
        self.assertEqual((cpu.r[5], cpu.r[6], cpu.r[1]), (7, 1, 0x0400))


class Cycles(unittest.TestCase):
    def cyc(self, src):
        cpu, _ = build(src + '\n nop', HDR)
        cpu.step(); cpu.step()                    # WDT + SP kurulumu
        c0 = cpu.cycles
        cpu.step()
        return cpu.cycles - c0

    def test_table(self):
        for src, n in {'mov r5, r6': 1, 'mov @r5, r6': 2, 'mov #1234, &0x0200': 5, 'mov #1, r5': 1,
                       'mov #1234, r5': 2, 'push r5': 3, 'call #0xC000': 5, 'jmp $+4': 2,
                       'mov 2(r5), r6': 3, 'mov r5, 2(r6)': 4, 'rra r5': 1}.items():
            self.assertEqual(self.cyc(src), n, src)


class Peripherals(unittest.TestCase):
    def test_wdt_resets_when_not_held(self):
        res = assemble('.org 0xC000\nstart: nop\n jmp start\n.org 0xFFFE\n.word start\n')
        cpu = MSP430()
        cpu.load(res.image)
        cpu.run(40000)
        self.assertTrue(any('WDT' in m for m in cpu.log))

    def test_gpio_led_and_button_irq(self):
        src = '''
        .org 0xC000
start:  mov #WDTPW|WDTHOLD, &WDTCTL
        mov #__STACK_END, SP
        bis.b #BIT0, &P1DIR
        bis.b #BIT3, &P1IES
        bis.b #BIT3, &P1IE
        eint
loop:   bis #CPUOFF, SR
        jmp loop
isr:    xor.b #BIT0, &P1OUT
        bic.b #BIT3, &P1IFG
        reti
        .org PORT1_VECTOR
        .word isr
        '''
        res = assemble(src)
        self.assertFalse(res.errors, res.errors)
        cpu = MSP430()
        cpu.load(res.image)
        cpu.r[0] = res.symbols['start']
        self.assertEqual(cpu.run(200), 'sleep')
        for want in (1, 0, 1):
            cpu.p1.set_input(3, 0)       # basildi (dusen kenar)
            cpu.p1.set_input(3, 1)
            cpu.run(100)
            self.assertEqual(cpu.p1.rg[1] & 1, want)

    def test_timer_interrupt_exact(self):
        src = '''
        .org 0xC000
start:  mov #WDTPW|WDTHOLD, &WDTCTL
        mov #__STACK_END, SP
        mov #1000, &TA0CCR0
        mov #CCIE, &TA0CCTL0
        mov #TASSEL_2|MC_1, &TA0CTL
        eint
        bis #CPUOFF, SR
        jmp $
isr:    mov.b #1, &P1OUT
        bic #CPUOFF, 0(SP)
        reti
        '''
        res = assemble(src + '.org TIMER0_A0_VECTOR\n.word isr\n')
        self.assertFalse(res.errors, res.errors)
        cpu = MSP430()
        cpu.load(res.image)
        cpu.r[0] = res.symbols['start']
        while not cpu.p1.rg[1] and cpu.cycles < 100000:
            cpu.step()
        self.assertEqual(cpu.p1.rg[1], 1)
        # CCR0=1000 -> 1001 tick sonra bayrak; kurulumdan sonra ~1000 cycle
        self.assertTrue(1000 < cpu.cycles < 1100, cpu.cycles)

    def test_uart_hello_and_rx(self):
        src = HDR + '''
        mov #msg, r5
nxt:    tst.b 0(r5)
        jz done
w:      bit.b #UCA0TXIFG, &IFG2
        jz w
        mov.b @r5+, &UCA0TXBUF
        jmp nxt
done:   jmp $
msg:    .asciz "Hello"
        .org 0xFFFE
        .word start
        '''
        res = assemble(src)
        self.assertFalse(res.errors, res.errors)
        cpu = MSP430()
        cpu.load(res.image)
        cpu.run(5000)
        self.assertEqual(bytes(cpu.uart.out), b'Hello')

    def test_flash_write_warns(self):
        cpu, _ = run('mov #5, &0xC100')
        self.assertTrue(any('0xC100' in m or '0C100' in m.upper() for m in cpu.log))


class Programs(unittest.TestCase):
    def test_fib(self):
        cpu, _ = run('''
        mov #0, r5
        mov #1, r6
        mov #10, r7
l:      mov r6, r8
        add r5, r6
        mov r8, r5
        dec r7
        jnz l
        mov r5, &0x0200''')
        self.assertEqual(cpu.mem.rw(0x0200), 55)

    def test_running_off_program_end_stops(self):
        res = assemble('.org 0xC000\nRESET: mov #6, r4\n nop\n.org 0xFFFE\n.word RESET\n')
        cpu = MSP430()
        cpu.load(res.image)
        self.assertEqual(cpu.run(10000), 'end')
        self.assertEqual((cpu.r[4], cpu.r[0]), (6, 0xC006))


class Examples(unittest.TestCase):
    def test_all_assemble(self):
        from pathlib import Path
        files = list(Path('msp430sim/examples').glob('*.asm'))
        self.assertEqual(len(files), 7)
        for f in files:
            self.assertFalse(assemble(f.read_text()).errors, f.name)

    def test_bubble_sort_runs_and_sorts_array(self):
        from pathlib import Path
        src = (Path('msp430sim/examples') / 'bubble_sort.asm').read_text()
        res = assemble(src)
        self.assertFalse(res.errors, res.errors)
        cpu = MSP430()
        cpu.load(res.image)
        self.assertEqual(cpu.run(100000), 'halt')
        vals = [cpu.mem.rw(0x0200 + 2 * i) for i in range(8)]
        self.assertEqual(vals, sorted(vals))

    def test_uart_hello_echoes(self):
        from pathlib import Path
        src = (Path('msp430sim/examples') / 'uart_hello.asm').read_text()
        res = assemble(src)
        cpu = MSP430()
        cpu.load(res.image)
        cpu.run(100000)
        self.assertEqual(bytes(cpu.uart.out), b'Hello, MSP430!\r\n')
        cpu.uart.receive(ord('X'))
        cpu.run(20000)
        self.assertEqual(bytes(cpu.uart.out), b'Hello, MSP430!\r\nX')


class Reference(unittest.TestCase):
    def test_help_covers_all_mnemonics(self):
        from msp430sim import asm, ref
        doc = ' '.join(r[0] + ' ' + r[1] for r in ref.INSNS).lower().replace('/', ' ')
        for n in {*asm.FMT1, *asm.FMT2, *asm.JUMPS, *asm.EMU}:
            self.assertIn(n, doc.replace('|', ' ').split(), n) if n not in ('clrc', 'setc', 'clrz', 'setz', 'clrn', 'setn', 'eint', 'dint') else self.assertIn(n, doc)


class AsmRobustness(unittest.TestCase):
    def test_no_crash_on_bad_input(self):
        for src in ('.asciz "abc', 'mov #1<<-1, r5', '.byte "\\x"', 'mov #1/0, r5', '.space -1'):
            res = assemble('.org 0xC000\n' + src + '\n')
            self.assertTrue(res.errors, src)

    def test_non_ascii_string_is_utf8(self):
        res = assemble('.org 0xC000\n.asciz "Çok"\n')
        self.assertFalse(res.errors, res.errors)
        self.assertEqual(res.image[0xC000], 'Çok'.encode() + b'\0')

    def test_typo_at_column0_is_not_silent(self):
        res = assemble('.org 0xC000\nnopp\n')
        self.assertTrue(res.warnings and 'nop' in res.warnings[0][1], res.warnings)
        res = assemble('.org 0xC000\nmvo r5, r6\n')
        self.assertTrue(res.errors and 'mvo' in res.errors[0][1] and 'mov' in res.errors[0][1], res.errors)

    def test_value_truncation_warns(self):
        for src in ('.byte 300', '.word 70000', 'mov #70000, r5', 'mov.b #300, r5'):
            res = assemble('.org 0xC000\n' + src + '\n')
            self.assertFalse(res.errors, res.errors)
            self.assertTrue(res.warnings, src)
        res = assemble('.org 0xC000\n.byte -1, 255\n.word -1, 65535\nmov #0xFFFF, r5\n')
        self.assertFalse(res.warnings, res.warnings)

    def test_number_formats(self):
        self.assertEqual(words('mov #0FFh, r5')[1], 0xFF)
        self.assertEqual(words('mov #%101, r5')[1], 5)
        self.assertEqual(words('mov #101b, r5')[1], 5)
        self.assertEqual(words('mov #18%5, r5')[1], 3)          # % hala modulo


class Symbols(unittest.TestCase):
    def test_common_ti_symbols(self):
        src = """.org 0xC000
start: mov.b &CALBC1_16MHZ, &BCSCTL1
       mov.b &CALDCO_16MHZ, &DCOCTL
       mov #TASSEL_2|MC_1|ID_3, &TACTL
       mov #1000, &TACCR0
       mov #CCIE, &TACCTL0
       bis.b #DIVA_3|XCAP_3|LFXT1S_2, &BCSCTL3
       bis.b #RSEL0|DCO0|DIVS_3|DIVM_3, &BCSCTL2
       mov #WDT_ARST_1000, &WDTCTL
       mov #LPM0_bits|GIE, SR
       mov #UCSSEL_2|UCMODE_0, r5
       mov #C|Z|N|V, r5
"""
        res = assemble(src)
        self.assertFalse(res.errors, res.errors)


class PullUp(unittest.TestCase):
    def test_ren_pull_up_and_pull_down(self):
        cpu, _ = run('bis.b #0x10, &P1REN\n bis.b #0x10, &P1OUT\n mov.b &P1IN, r5')
        self.assertTrue(cpu.r[5] & 0x10)
        cpu, _ = run('bis.b #0x10, &P1REN\n mov.b &P1IN, r5')
        self.assertFalse(cpu.r[5] & 0x10)
        cpu, _ = run('mov.b &P1IN, r5')
        self.assertFalse(cpu.r[5] & 0x10)           # yuzen pin: 0

    def test_released_button_floats_back_to_pull_up(self):
        cpu, _ = run('bis.b #0x10, &P1REN\n bis.b #0x10, &P1OUT')
        cpu.p1.set_input(4, 0)                      # surulen 0 pull-up'i yener
        self.assertFalse(cpu.p1.pins() & 0x10)
        cpu.p1.set_input(4, None)                   # birakinca pull-up 1 yapar
        self.assertTrue(cpu.p1.pins() & 0x10)

    def test_enabling_pull_up_sets_ifg_on_rising_edge(self):
        cpu, _ = run('bis.b #0x10, &P1REN\n bic.b #0x10, &P1IES\n bic.b #0x10, &P1IFG\n bis.b #0x10, &P1OUT')
        self.assertTrue(cpu.p1.rg[3] & 0x10)


class UartTx(unittest.TestCase):
    def test_write_while_busy_is_dropped_with_warning(self):
        cpu, _ = run('mov.b #65, &UCA0TXBUF\n mov.b #66, &UCA0TXBUF\n mov.b #67, &UCA0TXBUF')
        self.assertEqual(bytes(cpu.uart.out), b'A')
        self.assertTrue(any('TXIFG' in m for m in cpu.log), cpu.log)


class Gui(unittest.TestCase):
    def setUp(self):
        try:
            from msp430sim.gui import App
            self.app = App()
        except Exception as e:                    # tkinter yok veya ekran yok
            raise unittest.SkipTest(str(e))
        self.app.withdraw()

    def tearDown(self):
        self.app.destroy()

    def test_editing_invalidates_assembled_result(self):
        a = self.app
        self.assertTrue(a.do_assemble())
        self.assertIsNotNone(a.result)
        a.editor.insert('end', '\n nop')
        a.update()
        self.assertIsNone(a.result)


if __name__ == '__main__':
    unittest.main()
