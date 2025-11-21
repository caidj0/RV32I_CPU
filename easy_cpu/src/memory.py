from assassyn.frontend import *
from instruction import MO_LEN, WBF_LEN, MemoryOperation
from reg_file import RegFile
from utils import Bool, forward_ports, peek_or


class Memory(Module):
    instruction_addr: Port
    rd: Port
    rs1: Port
    rs2: Port
    imm: Port
    memory_operation: Port
    is_branch: Port
    branch_flip: Port
    change_PC: Port
    write_back_from: Port
    alu_result: Port

    def __init__(self):
        super().__init__(
            ports={
                "instruction_addr": Port(Bits(32)),
                "rd": Port(Bits(5)),
                "rs1": Port(Bits(32)),
                "rs2": Port(Bits(32)),
                "imm": Port(Bits(32)),
                "memory_operation": Port(Bits(MO_LEN)),
                "is_branch": Port(Bool),
                "branch_flip": Port(Bool),
                "change_PC": Port(Bool),
                "write_back_from": Port(Bits(WBF_LEN)),
                "alu_result": Port(Bits(32)),
            }
        )

    @module.combinational
    def build(self, dcache: SRAM, write_back: Module):
        need_mem = self.memory_operation.valid()

        memory_operation = peek_or(self.memory_operation, Bits(MO_LEN)(0))
        alu_result = self.alu_result.peek()
        addr = need_mem.select(alu_result, Bits(32)(0))
        raw_wdata = peek_or(self.rs2, Bits(32)(0))

        raw_re = memory_operation <= Bits(MO_LEN)(MemoryOperation.LOAD_HALFU.value)
        re = need_mem & raw_re
        we = need_mem & (~raw_re)

        wdata = memory_operation.case(
            {
                None: raw_wdata,  # pyright: ignore[reportArgumentType]
                Bits(MO_LEN)(MemoryOperation.STORE_BYTE.value): raw_wdata & Bits(32)(0xFF),
                Bits(MO_LEN)(MemoryOperation.STORE_HALF.value): raw_wdata & Bits(32)(0xFFFF),
            }
        )

        dcache.build(we, re, addr, wdata)

        forward_ports(
            write_back,
            [
                self.instruction_addr,
                self.rd,
                self.rs1,
                self.rs2,
                self.imm,
                self.memory_operation,
                self.is_branch,
                self.branch_flip,
                self.change_PC,
                self.write_back_from,
                self.alu_result,
            ],
        )

        write_back.async_called()
