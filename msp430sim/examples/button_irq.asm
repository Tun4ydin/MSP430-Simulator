; S2 butonu (P1.3) kesmesi ile P1.0 LED'ini degistirir. CPU uykuda (LPM4 benzeri) bekler.
; I/O panelinde P1.3'e tiklayin (basma = dusen kenar).
        .org 0xC000
start:  mov   #WDTPW|WDTHOLD, &WDTCTL
        mov   #__STACK_END, SP
        bis.b #BIT0, &P1DIR
        bic.b #BIT0, &P1OUT
        bis.b #BIT3, &P1REN             ; pull-up (LaunchPad'de harici de var)
        bis.b #BIT3, &P1OUT
        bis.b #BIT3, &P1IES             ; yuksek -> alcak kenar
        bic.b #BIT3, &P1IFG
        bis.b #BIT3, &P1IE
        bis   #CPUOFF|GIE, SR           ; uyu, kesme bekle
        jmp   $
port1:  xor.b #BIT0, &P1OUT
        bic.b #BIT3, &P1IFG             ; bayragi yazilimla sil
        reti
        .org PORT1_VECTOR
        .word port1
        .org RESET_VECTOR
        .word start
