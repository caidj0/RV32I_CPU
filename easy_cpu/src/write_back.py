from assassyn.frontend import *
from memory import Memory
from reg_file import RegFile
from utils import Bool, pop_or


class WriteBack(Module):
    verbose: bool

    instruction_addr: Port
    rd: Port
    rs1: Port
    imm: Port
    is_branch: Port
    branch_flip: Port
    change_PC: Port
    is_jalr: Port

    def __init__(self, verbose: bool):
        super().__init__(
            ports={
                "instruction_addr": Port(Bits(32)),
                "rd": Port(Bits(5)),
                "rs1": Port(Bits(32)),
                "imm": Port(Bits(32)),
                "is_branch": Port(Bool),
                "branch_flip": Port(Bool),
                "change_PC": Port(Bool),
                "is_jalr": Port(Bool),
            }
        )
        self.verbose = verbose

    @module.combinational
    def build(self, reg_file: RegFile, memory: Memory):
        instruction_addr = pop_or(self.instruction_addr, Bits(32)(0))
        rd = pop_or(self.rd, Bits(5)(0))
        rs1 = pop_or(self.rs1, Bits(32)(0))
        imm = pop_or(self.imm, Bits(32)(0))
        is_branch = pop_or(self.is_branch, Bool(0))
        branch_flip = pop_or(self.branch_flip, Bool(0))
        change_PC = pop_or(self.change_PC, Bool(0))
        is_jalr = pop_or(self.is_jalr, Bool(0))

        out = memory.get_out()

        reg_file.build(rd, out)

        with Condition(is_branch | change_PC):
            flush_PC = is_jalr.select(rs1, instruction_addr)

            branch_success = (out != Bits(32)(0)) ^ branch_flip
            branch_offset = (change_PC | branch_success).select(imm, Bits(32)(4))

        log_parts = ["instruction_addr=0x{:08X}"]
        for i in range(32):
            log_parts.append(f"x{i}=0x{{:08X}}")
        log_format = " ".join(log_parts)
        new_regs = [(rd == Bits(5)(i)).select(out, reg_file.regs[i]) for i in range(32)]
        new_regs[0] = reg_file.regs[0]
        log(log_format, instruction_addr, *new_regs)

        return flush_PC, branch_offset, rd
