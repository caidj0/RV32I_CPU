# Easy CPU 
五级流水版本的 RV32I CPU

## 需要实现的指令

- 算术指令
    - addi
    - slti
    - sltiu
    - xori
    - ori
    - andi
    - slli
    - srli
    - srai
    - add  
    - sub 
    - sll  
    - slt  
    - sltu 
    - xor 
    - srl 
    - sra 
    - or 
    - and 
- Wait for Interrupt
    - wfi
- 访存指令
    - lb 
    - lh 
    - lw 
    - lbu 
    - lhu 
    - sb
    - sh 
    - sw 
- 跳转指令
    - jal
    - jalr
- 分支指令
    - beq
    - bne 
    - blt
    - bge
    - bltu
    - bgeu
- 其他指令
    - lui
    - auipc

其中分支指令，跳转指令可能需要 flush 流水线

## Fetch
> Ports: should_stall(b1), new_PC({valid: b1, PC: b32})

- 当 `should_tall` 为 1 时停顿；
- 若 new_PC 不 valid，则 PC = PC + 4，否则 PC = new_PC；
- 使用 new_PC/(PC + 4) 对 ICache 进行 bind。

## Decode 
> Ports: should_stall(b1)

- 当 `should_stall`  为 1 时停顿；
- 从 ICache 的寄存器中取出指令，进行解码：获取 rs1, rs2, rd，mem_type, ALU Operator Code 
- 对于跳转和分支指令，暂停解码直至解锁；对于数据冒险，暂停直至数据可用


## Execute
> Ports: rs1(b32), rs2(b32), rd(b5), mem_type(b2: None, Read, Write), ALU Operator Code(b{Code count}) 

## Memory
> Ports: rd, mem_type, value

## Writeback
> Ports: rd, value


## ICache
一个 Sram

## DCache
一个 Sram

## RegFile
> Ports: rd(b5), rd_data(b32), occupy_reg(b5), release_reg(b5)

一个 32 位的 reg array，还存储占用信息