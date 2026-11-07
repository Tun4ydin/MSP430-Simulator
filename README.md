# MSP430 Simulator (G2553) — kart gerektirmez

MARS tarzı masaüstü simülatör: assembly yaz → Assemble (F3) → Run (F5) / Step (F7). Saf Python + Tkinter, harici bağımlılık yok.

## Hızlı Başlangıç

En kolay yol — tek komutla çalıştırın (Tkinter destekli Python otomatik algılanır):

```bash
./run.sh                                    # veya: python3 run.py
```

### Diğer Kullanım Seçenekleri

```bash
python3 run.py msp430sim/examples/fib.asm   # Belirtilen dosyayı açarak GUI başlatır
python3 run.py --cli msp430sim/examples/fib.asm # GUI olmadan terminalde simüle eder
python3 run.py --assemble msp430sim/examples/fib.asm # Yalnızca derler ve blokları listeler

# Paket olarak kurmak isterseniz:
pip install -e .
msp430sim                                   # Global komut

# Testleri çalıştırmak için:
python3 -m unittest discover -s tests
```

## Neler var
- MSP430 (non-X) komut seti, tüm adresleme modları, constant generator, gerçek cycle sayımı, kesmeler, LPM.
- G2553 çevre birimleri: P1/P2 (LED/buton, kenar kesmesi), Timer_A0 (stop/up/continuous/up-down, CCR0/CCR1/CCR2/TAIV), WDT (reset ve interval), UART (UCA0, TX/RX + kesmeler).
- 3D kart görünümü (F9 / "3D Kart"): MSP-EXP430G2ET LaunchPad'in TI tasarım dosyalarından (SLAR153) üretilmiş gerçek ölçülü modeli. LED'ler (D1 yeşil = P1.0, D2 kırmızı = P1.6, D3 RGB = P2.1/P2.3/P2.5), header pinleri ve DIP bacakları lojik seviyeye göre renklenir, J101 TXD/RXD jumper'ları UART trafiğinde yanıp söner. S1 (P1.3) ve S2 (RESET) model üzerinde tıklanabilir; sürükle = döndür, sağ tık = kaydır, tekerlek = yakınlaş. Saf Tkinter, ek bağımlılık yok.
- GUI: editör, listing + breakpoint (Execute sekmesinde çift tık), register/flag/cycle paneli, bellek görüntüleyici, I/O paneli (P1.3 = S1 butonu), UART konsolu, hata listesi (çift tık satıra gider).

## Sözdizimi
`label:`, `;` veya `//` yorum, `MOV.B #1, &P1OUT`, emulated komutlar (NOP RET POP BR CLR INC DEC TST INV RLA ADC SBC EINT DINT ...).
Direktifler: `.org .word .byte .ascii .asciz .space .align .equ`. `msp430g2553.h` sembolleri hazır (`P1OUT`, `WDTCTL`, `TASSEL_2`, `RESET_VECTOR`, `__STACK_END` ...).
Reset vektörü: `.org RESET_VECTOR` + `.word start` (yazılmazsa `start`/`main` etiketi kullanılır).
`WDTCTL = WDTPW|WDTHOLD` yazmazsanız gerçek donanımdaki gibi ~32768 cycle sonra reset olur.

## Sınırlar
ADC10, Timer1_A, comparator, flash controller, SPI/I²C, capture ve PWM çıkış modları yok. BCS saat register'ları saklanır ama saati değiştirmez.
Kalibrasyon sabitleri `cpu.py` başında: `ACLK_DIV` (ACLK≈12 kHz), `UART_BITS`. Flash'a yazma yok sayılır (uyarı verir). Reset, RAM'deki `.org 0x0200` verisini geri yükler.
