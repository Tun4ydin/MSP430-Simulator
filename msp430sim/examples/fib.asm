; Ilk 10 Fibonacci sayisini RAM'e (0x0200...) yazar: 0 1 1 2 3 5 8 13 21 34
; Memory panelinde RAM bolgesine bakin.
        .org 0xC000
start:  mov   #WDTPW|WDTHOLD, &WDTCTL
        mov   #__STACK_END, SP
        mov   #0x0200, r4               ; hedef
        mov   #0, r5                    ; F(n)
        mov   #1, r6                    ; F(n+1)
        mov   #10, r7                   ; sayac
loop:   mov   r5, 0(r4)
        incd  r4
        mov   r6, r8
        add   r5, r6
        mov   r8, r5
        dec   r7
        jnz   loop
        jmp   $                         ; bitti (simulator burada durur)
        .org RESET_VECTOR
        .word start
