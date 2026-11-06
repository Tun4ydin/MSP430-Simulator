"""Yardim penceresi verisi (MARS 'Help' benzeri): komutlar, adresleme, direktifler, cycle tablolari."""

# (komut, sozdizimi, grup, islem, bayraklar CZNV, aciklama + ornek)
INSNS = [
    # --- Format I (iki operand) ---
    ('MOV', 'MOV[.B] src, dst', 'Veri', 'dst = src', '- - - -',
     'src degerini dst\'ye kopyalar. Bayrak etkilemez. .B ile register hedefte ust byte silinir.\n'
     'ornek: mov #0x1234, r5   ; r5 = 0x1234\n       mov.b &P1IN, r6  ; r6 = 0x00xx'),
    ('ADD', 'ADD[.B] src, dst', 'Aritmetik', 'dst = dst + src', '* * * *',
     'Toplama. C = elde, V = isaretli tasma.\nornek: add r5, r6   ; r6 += r5'),
    ('ADDC', 'ADDC[.B] src, dst', 'Aritmetik', 'dst = dst + src + C', '* * * *',
     'Elde ile toplama (cok kelimeli toplama icin).\nornek: add r4, r6 / addc r5, r7   ; 32 bit toplama'),
    ('SUB', 'SUB[.B] src, dst', 'Aritmetik', 'dst = dst - src', '* * * *',
     'Cikarma (dst + ~src + 1). C = 1 ise borrow YOK (dst >= src, isaretsiz).\nornek: sub #3, r5'),
    ('SUBC', 'SUBC[.B] src, dst', 'Aritmetik', 'dst = dst - src - 1 + C', '* * * *',
     'Borrow ile cikarma (cok kelimeli cikarma icin).'),
    ('CMP', 'CMP[.B] src, dst', 'Aritmetik', 'dst - src (sadece bayrak)', '* * * *',
     'Karsilastirir, sonucu saklamaz. Ardindan jeq/jne/jhs/jlo/jge/jl kullanilir.\n'
     'ornek: cmp #10, r5\n       jl  kucuk      ; r5 < 10 (isaretli)'),
    ('DADD', 'DADD[.B] src, dst', 'Aritmetik', 'dst = dst + src + C (BCD)', '* * * U',
     'Ondalik (BCD) toplama. V tanimsiz.\nornek: clrc / dadd #0x0001, r5   ; 0x0199 -> 0x0200'),
    ('BIT', 'BIT[.B] src, dst', 'Mantik', 'dst AND src (sadece bayrak)', '* * * 0',
     'Bit testi. Z=1 ise secilen bitlerin hepsi 0. C = !Z.\nornek: bit.b #BIT3, &P1IN\n       jz basili   ; P1.3 = 0'),
    ('BIC', 'BIC[.B] src, dst', 'Mantik', 'dst = dst AND ~src', '- - - -',
     'Bit silme (clear). Bayrak etkilemez.\nornek: bic.b #BIT0, &P1OUT   ; P1.0 = 0'),
    ('BIS', 'BIS[.B] src, dst', 'Mantik', 'dst = dst OR src', '- - - -',
     'Bit set. Bayrak etkilemez.\nornek: bis.b #BIT0, &P1DIR   ; P1.0 cikis\n       bis #CPUOFF, SR   ; uyku'),
    ('XOR', 'XOR[.B] src, dst', 'Mantik', 'dst = dst XOR src', '* * * *',
     'Ozel-veya. C = !Z. V = iki operand da negatifse 1.\nornek: xor.b #BIT0, &P1OUT   ; LED toggle'),
    ('AND', 'AND[.B] src, dst', 'Mantik', 'dst = dst AND src', '* * * 0',
     'Mantiksal ve. C = !Z.\nornek: and #0x00FF, r5'),
    # --- Format II (tek operand) ---
    ('RRC', 'RRC[.B] dst', 'Kaydirma', 'C -> MSB ... LSB -> C', '* * * 0',
     'Elde uzerinden saga dondurme (9/17 bit).\nornek: setc / rrc r5   ; MSB = 1'),
    ('RRA', 'RRA[.B] dst', 'Kaydirma', 'MSB -> MSB ... LSB -> C', '* * * 0',
     'Aritmetik saga kaydirma (isaret korunur) = isaretli /2.\nornek: rra r5'),
    ('SWPB', 'SWPB dst', 'Kaydirma', 'dst[15:8] <-> dst[7:0]', '- - - -',
     'Byte\'lari yer degistirir (sadece word).\nornek: swpb r5   ; 0x1234 -> 0x3412'),
    ('SXT', 'SXT dst', 'Kaydirma', 'bit7 -> bit15..8', '* * * 0',
     'Byte\'i word\'e isaret genisletir. C = !Z.\nornek: sxt r5   ; 0x0080 -> 0xFF80'),
    ('PUSH', 'PUSH[.B] src', 'Stack', 'SP -= 2; @SP = src', '- - - -',
     'Stack\'e iter. Byte iterse de SP 2 azalir.\nornek: push r5'),
    ('CALL', 'CALL dst', 'Dallanma', 'push PC; PC = dst', '- - - -',
     'Alt programi cagirir. Donus adresi stack\'e iter.\nornek: call #fonk'),
    ('RETI', 'RETI', 'Dallanma', 'SR = pop; PC = pop', 'hepsi', 'Kesme servisinden doner (SR ve PC geri yuklenir). 5 cycle.'),
    # --- Jump ---
    ('JMP', 'JMP etiket', 'Dallanma', 'PC += 2*ofset', '- - - -', 'Kosulsuz dallanma. Menzil -1024..+1022 byte. Uzak hedef: br #hedef.\n"jmp $" = sonsuz dongu.'),
    ('JNE/JNZ', 'JNZ etiket', 'Dallanma', 'if Z=0', '- - - -', 'Esit degilse atla (Z=0).'),
    ('JEQ/JZ', 'JZ etiket', 'Dallanma', 'if Z=1', '- - - -', 'Esitse atla (Z=1).'),
    ('JNC/JLO', 'JNC etiket', 'Dallanma', 'if C=0', '- - - -', 'Elde yoksa atla. Isaretsiz "kucuk" (dst < src, cmp sonrasi).'),
    ('JC/JHS', 'JC etiket', 'Dallanma', 'if C=1', '- - - -', 'Elde varsa atla. Isaretsiz "buyuk veya esit" (cmp sonrasi).'),
    ('JN', 'JN etiket', 'Dallanma', 'if N=1', '- - - -', 'Negatifse atla.'),
    ('JGE', 'JGE etiket', 'Dallanma', 'if (N xor V)=0', '- - - -', 'Isaretli buyuk veya esit.'),
    ('JL', 'JL etiket', 'Dallanma', 'if (N xor V)=1', '- - - -', 'Isaretli kucuk.'),
    # --- Emulated (assembler gercek komuta cevirir) ---
    ('NOP', 'NOP', 'Emulated', 'mov r3, r3', '- - - -', 'Hicbir sey yapmaz (1 cycle).'),
    ('RET', 'RET', 'Emulated', 'mov @sp+, pc', '- - - -', 'Alt programdan doner.'),
    ('POP', 'POP dst', 'Emulated', 'mov @sp+, dst', '- - - -', 'Stack\'ten ceker.'),
    ('BR', 'BR dst', 'Emulated', 'mov dst, pc', '- - - -', 'Uzun dallanma (tum 64 KB).\nornek: br #hedef'),
    ('CLR', 'CLR[.B] dst', 'Emulated', 'mov #0, dst', '- - - -', 'dst = 0.'),
    ('INC', 'INC[.B] dst', 'Emulated', 'add #1, dst', '* * * *', 'dst += 1.'),
    ('INCD', 'INCD[.B] dst', 'Emulated', 'add #2, dst', '* * * *', 'dst += 2.'),
    ('DEC', 'DEC[.B] dst', 'Emulated', 'sub #1, dst', '* * * *', 'dst -= 1.\nornek: dec r15 / jnz dongu'),
    ('DECD', 'DECD[.B] dst', 'Emulated', 'sub #2, dst', '* * * *', 'dst -= 2.'),
    ('TST', 'TST[.B] dst', 'Emulated', 'cmp #0, dst', '* * * *', 'dst\'yi 0 ile karsilastirir (Z, N).'),
    ('INV', 'INV[.B] dst', 'Emulated', 'xor #-1, dst', '* * * *', 'Bitleri ters cevirir.'),
    ('RLA', 'RLA[.B] dst', 'Emulated', 'add dst, dst', '* * * *', 'Sola kaydirma (x2).'),
    ('RLC', 'RLC[.B] dst', 'Emulated', 'addc dst, dst', '* * * *', 'Elde ile sola dondurme.'),
    ('ADC', 'ADC[.B] dst', 'Emulated', 'addc #0, dst', '* * * *', 'dst += C.'),
    ('SBC', 'SBC[.B] dst', 'Emulated', 'subc #0, dst', '* * * *', 'dst -= (1 - C).'),
    ('DADC', 'DADC[.B] dst', 'Emulated', 'dadd #0, dst', '* * * U', 'BCD: dst += C.'),
    ('CLRC / SETC', 'CLRC | SETC', 'Emulated', 'bic/bis #1, sr', 'C', 'Elde bayragini siler / set eder.'),
    ('CLRZ / SETZ', 'CLRZ | SETZ', 'Emulated', 'bic/bis #2, sr', 'Z', 'Z bayragini siler / set eder.'),
    ('CLRN / SETN', 'CLRN | SETN', 'Emulated', 'bic/bis #4, sr', 'N', 'N bayragini siler / set eder.'),
    ('EINT / DINT', 'EINT | DINT', 'Emulated', 'bis/bic #8, sr', 'GIE', 'Kesmeleri acar / kapatir (GIE).'),
]

ADDRESSING = [
    ('Register', 'Rn', 'Operand = Rn', 'mov r5, r6', 'src + dst'),
    ('Indexed', 'X(Rn)', 'Operand = bellek[Rn + X]', 'mov 2(r5), r6', 'src + dst'),
    ('Symbolic', 'ETIKET', 'Operand = bellek[ETIKET] (PC-goreli)', 'mov deger, r6', 'src + dst'),
    ('Absolute', '&ADRES', 'Operand = bellek[ADRES]', 'mov.b &P1IN, r6', 'src + dst'),
    ('Indirect', '@Rn', 'Operand = bellek[Rn]', 'mov @r5, r6', 'sadece src'),
    ('Indirect autoincrement', '@Rn+', 'Operand = bellek[Rn]; sonra Rn += 1 (.B) veya 2 (.W)', 'mov.b @r5+, r6', 'sadece src'),
    ('Immediate', '#N', 'Operand = N sabiti', 'mov #1234, r5', 'sadece src'),
    ('Constant generator', '#0 #1 #2 #4 #8 #-1', 'Ek kelime kullanmaz (R2/R3 ile uretilir): 1 kelime, hizli', 'mov #0, r5', 'sadece src'),
]

DIRECTIVES = [
    ('.org ADRES', 'Sonraki kodun/verinin adresini ayarlar.', '.org 0xC000'),
    ('.text', 'Program belleginde (0xC000) devam eder.', '.text'),
    ('.sect ".reset"', 'Reset vektoru (0xFFFE). ".intNN" -> 0xFFE0 + 2*NN. ".stack" yok sayilir.', '.sect ".reset"\n.short RESET'),
    ('.word / .short', '16 bitlik deger(ler) koyar.', '.word 1, 2, etiket'),
    ('.byte', '8 bitlik deger(ler) veya metin koyar.', '.byte 0x41, "AB"'),
    ('.ascii / .asciz / .string', 'Metin koyar (.asciz ve .string sonuna 0 ekler).', 'msg: .asciz "Merhaba"'),
    ('.space N[, v] / .skip', 'N byte ayirir (varsayilan 0).', '.space 16'),
    ('.align N', 'Adresi N\'in katina hizalar.', '.align 2'),
    ('.equ / .set', 'Sabit tanimlar.', 'N .equ 10   veya   .equ N, 10'),
    ('.cdecls .def .retain .retainrefs .global', 'CCS uyumlulugu icin yok sayilir (msp430.h sabitleri zaten tanimli).', ''),
    ('Etiket', '"ad:" veya sutun 0\'da "ad". "$" = gecerli adres.', 'dongu: jmp dongu / jmp $'),
    ('Ifadeler', 'Ondalik, 0x.., 0b.., \'c\'; + - * / & | ^ ~ << >> ( ).', '#(BIT0|BIT6)'),
    ('Yorum', '";" veya "//" satir sonuna kadar.', 'nop ; yorum'),
]

CYCLES = '''Format I (iki operand) - kaynak (satir) x hedef (sutun), cycle:
                  Rm   x(Rm)/EDE/&EDE
  Rn               1       4        (hedef PC ise 2)
  @Rn / @Rn+       2       5
  #N               2       5        (#0,#1,#2,#4,#8,#-1 -> Rn gibi: 1 / 4)
  x(Rn)/EDE/&EDE   3       6

Format II (tek operand):
                  RRA/RRC/SWPB/SXT   PUSH   CALL
  Rn                    1              3      4
  @Rn                   3              4      4
  @Rn+                  3              4      5
  #N                    -              4      5
  x(Rn)/EDE/&EDE        4              5      5

Jump: 2 cycle (dallansa da dallanmasa da)      RETI: 5 cycle
Kesme girisi: 6 cycle    Sabit sayilar: ekrandaki "Cycle" sayaci bunlari toplar.
LPM (CPUOFF=1): CPU durur, sayac cevre birimi olayina kadar ileri sarilir.
MCLK = SMCLK = 1 MHz varsayilir: 1 cycle = 1 us.
'''

INTERRUPTS = [
    ('PORT1', '0xFFE4', 'P1IFG & P1IE', 'P1IFG\'yi yazilimla silin'),
    ('PORT2', '0xFFE6', 'P2IFG & P2IE', 'P2IFG\'yi yazilimla silin'),
    ('USCIAB0TX', '0xFFEC', 'UCA0TXIFG & UCA0TXIE', 'TXBUF yazinca silinir'),
    ('USCIAB0RX', '0xFFEE', 'UCA0RXIFG & UCA0RXIE', 'RXBUF okununca silinir'),
    ('TIMER0_A1', '0xFFF0', 'TA0CCR1/CCR2/TAIFG', 'TA0IV okununca en yuksek bayrak silinir'),
    ('TIMER0_A0', '0xFFF2', 'TA0CCR0 (CCIFG0)', 'Servis girince otomatik silinir'),
    ('WDT', '0xFFF4', 'WDTIFG (interval modu)', 'Otomatik silinir'),
    ('RESET', '0xFFFE', 'acilis / WDT / PUC', 'Program baslangici'),
]

NOTES = '''Kesme akisi: komut sinirinda GIE=1 ve bekleyen kesme varsa -> PC ve SR stack'e itilir, SR silinir
(GIE ve CPUOFF dahil), PC = vektor. RETI SR ve PC'yi geri yukler (uyku bitini de).
ISR icinden uyandirmak icin: bic #CPUOFF, 0(SP) (yigindaki SR'yi degistirir), sonra reti.
WDT: acilista calisir; main'in basinda mov #WDTPW|WDTHOLD, &WDTCTL yazilmazsa ~32 ms'de reset atar.
Flash (0xC000+) yazilamaz, RAM 0x0200-0x03FF, __STACK_END = 0x0400.
'''
