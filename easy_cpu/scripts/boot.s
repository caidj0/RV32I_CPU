    .global _start
_start:
    call main 
    ebreak
1: 
    j 1b
