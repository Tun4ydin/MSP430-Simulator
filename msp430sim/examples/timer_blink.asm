; Timer_A CCR0 kesmesi ile P1.0 ve P1.6 dönüşümlü yanıp söner. CPU LPM0'da uyur.
; SMCLK = 1 MHz, CCR0 = 50000 -> 50 ms; 10 kesmede bir LED degisir (0.5 sn).
        .org 0xC000
start:  mov   #WDTPW|WDTHOLD, &WDTCTL
        mov   #__STACK_END, SP
        bis.b #BIT0|BIT6, &P1DIR
        mov.b #BIT0, &P1OUT
        mov   #10, r10                  ; kesme sayaci
        mov   #50000, &TA0CCR0
        mov   #CCIE, &TA0CCTL0
        mov   #TASSEL_2|MC_1, &TA0CTL   ; SMCLK, up modu
        bis   #LPM0_bits|GIE, SR
        jmp   $
ta0:    dec   r10
        jnz   out
        mov   #10, r10
        xor.b #BIT0|BIT6, &P1OUT
out:    reti
        .org TIMER0_A0_VECTOR
        .word ta0
        .org RESET_VECTOR
        .word start
