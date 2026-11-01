.text
.globl seed
seed:
    .byte 0x0f, 0xff # Deliberately invalid decoder test data.
    ret
