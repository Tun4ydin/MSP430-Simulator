; P1.0 (LED1/D1: G2ET'de yesil, eski G2 kartta kirmizi) gecikme dongusuyle yanip soner.
; Hizi "1 MHz" yapin: yaklasik 0.2 sn araliklarla yanar.
        .org 0xC000
start:  mov   #WDTPW|WDTHOLD, &WDTCTL   ; watchdog'u durdur (unutulursa reset atar!)
        mov   #__STACK_END, SP
        bis.b #BIT0, &P1DIR             ; P1.0 cikis
loop:   xor.b #BIT0, &P1OUT             ; LED degistir
        mov   #20000, r15
delay:  dec   r15                       ; 3 cycle x 20000 = 60000 cycle
        jnz   delay
        jmp   loop
        .org RESET_VECTOR
        .word start
