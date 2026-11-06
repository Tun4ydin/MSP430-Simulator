; RAM'deki 8 elemanli diziyi kabarcik siralamasiyla kucukten buyuge siralar.
; Reset siralanmamis hali geri yukler (MARS .data gibi).
        .equ N, 8
        .org 0x0200
arr:    .word 9, 3, 7, 1, 8, 2, 6, 4
        .org 0xC000
start:  mov   #WDTPW|WDTHOLD, &WDTCTL
        mov   #__STACK_END, SP
        mov   #N-1, r10                 ; dis dongu sayaci
outer:  mov   #arr, r4
        mov   r10, r11                  ; ic dongu sayaci
inner:  cmp   2(r4), 0(r4)              ; 0(r4) - 2(r4)
        jlo   noswap                    ; isaretsiz kucukse takas yok (C=0 -> jlo)
        jeq   noswap
        mov   0(r4), r12
        mov   2(r4), 0(r4)
        mov   r12, 2(r4)
noswap: incd  r4
        dec   r11
        jnz   inner
        dec   r10
        jnz   outer
        jmp   $
        .org RESET_VECTOR
        .word start
