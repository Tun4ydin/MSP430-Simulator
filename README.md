# MSP430 Simulator (G2553) — kart gerektirmez

MARS tarzı masaüstü simülatör: assembly yaz → Assemble (F3) → Run (F5) / Step (F7). Saf Python + Tkinter, bağımlılık yok.

```
/usr/local/bin/python3 -m msp430sim        # Tk destekli Python gerekir
/usr/local/bin/python3 -m unittest discover -s tests -t .
```
(`python3` Homebrew 3.15 sürümünde tkinter yok; `python-tk` kurun veya Tk'li bir Python kullanın.)

## Neler var
- MSP430 (non-X) komut seti, tüm adresleme modları, constant generator, gerçek cycle sayımı, kesmeler, LPM.
- G2553 çevre birimleri: P1/P2 (LED/buton, kenar kesmesi), Timer_A0 (stop/up/continuous/up-down, CCR0/CCR1/CCR2/TAIV), WDT (reset ve interval), UART (UCA0, TX/RX + kesmeler).
- GUI: editör, listing + breakpoint (Execute sekmesinde çift tık), register/flag/cycle paneli, bellek görüntüleyici, I/O paneli (P1.3 = S2 butonu), UART konsolu, hata listesi (çift tık satıra gider).

## Sözdizimi
`label:`, `;` veya `//` yorum, `MOV.B #1, &P1OUT`, emulated komutlar (NOP RET POP BR CLR INC DEC TST INV RLA ADC SBC EINT DINT ...).
Direktifler: `.org .word .byte .ascii .asciz .space .align .equ`. `msp430g2553.h` sembolleri hazır (`P1OUT`, `WDTCTL`, `TASSEL_2`, `RESET_VECTOR`, `__STACK_END` ...).
Reset vektörü: `.org RESET_VECTOR` + `.word start` (yazılmazsa `start`/`main` etiketi kullanılır).
`WDTCTL = WDTPW|WDTHOLD` yazmazsanız gerçek donanımdaki gibi ~32768 cycle sonra reset olur.

## Sınırlar
ADC10, Timer1_A, comparator, flash controller, SPI/I²C, capture ve PWM çıkış modları yok. BCS saat register'ları saklanır ama saati değiştirmez.
Kalibrasyon sabitleri `cpu.py` başında: `ACLK_DIV` (ACLK≈12 kHz), `UART_BITS`. Flash'a yazma yok sayılır (uyarı verir). Reset, RAM'deki `.org 0x0200` verisini geri yükler.
