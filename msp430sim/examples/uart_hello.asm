; UART: "Hello" yazar, sonra Console'a yazdiginiz her karakteri yankilar (RX kesmesi).
        .org 0xC000
start:  mov   #WDTPW|WDTHOLD, &WDTCTL
        mov   #__STACK_END, SP
        bis.b #UCSWRST, &UCA0CTL1
        mov.b #UCSSEL_2, &UCA0CTL1      ; SMCLK
        mov.b #104, &UCA0BR0            ; 9600 baud @ 1 MHz
        mov.b #0, &UCA0BR1
        bic.b #UCSWRST, &UCA0CTL1
        mov   #msg, r5
next:   tst.b 0(r5)
        jz    done
wait:   bit.b #UCA0TXIFG, &IFG2
        jz    wait
        mov.b @r5+, &UCA0TXBUF
        jmp   next
done:   bis.b #UCA0RXIE, &IE2
        bis   #CPUOFF|GIE, SR
        jmp   $
rx:     bit.b #UCA0TXIFG, &IFG2
        jz    rx
        mov.b &UCA0RXBUF, &UCA0TXBUF    ; oku (RXIFG silinir) ve geri gonder
        reti
msg:    .asciz "Hello, MSP430!\r\n"
        .org USCIAB0RX_VECTOR
        .word rx
        .org RESET_VECTOR
        .word start
