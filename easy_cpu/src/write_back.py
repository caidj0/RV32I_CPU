from tabnanny import verbose
from assassyn.frontend import *
from instruction import MO_LEN, WBF_LEN, MemoryOperation, WriteBackFrom
from memory import Memory
from reg_file import RegFile, RegOccupation
from utils import Bool, pop_or, sext, to_one_hot


class WriteBack(Module):
    verbose: bool

    instruction_addr: Port
    rd: Port
    imm: Port
    is_branch: Port
    branch_flip: Port
    change_PC: Port
    write_back_from: Port

    def __init__(self, verbose: bool):
        super().__init__(
            ports={
                "instruction_addr": Port(Bits(32)),
                "rd": Port(Bits(5)),
                "imm": Port(Bits(32)),
                "is_branch": Port(Bool),
                "branch_flip": Port(Bool),
                "change_PC": Port(Bool),
                "write_back_from": Port(Bits(WBF_LEN)),
            }
        )
        self.verbose = verbose

    @module.combinational
    def build(self, reg_file: RegFile, memory: Memory):
        instruction_addr = pop_or(self.instruction_addr, Bits(32)(0))
        rd = pop_or(self.rd, Bits(5)(0))
        imm = pop_or(self.imm, Bits(32)(0))
        is_branch = pop_or(self.is_branch, Bool(0))
        branch_flip = pop_or(self.branch_flip, Bool(0))
        change_PC = pop_or(self.change_PC, Bool(0))
        write_back_from = pop_or(self.write_back_from, Bits(WBF_LEN)(0))

        out = memory.get_out()

        data = to_one_hot(write_back_from, len(WriteBackFrom)).select1hot(*[out, instruction_addr + Bits(32)(4)])

        reg_file.build(rd, data)

        with Condition(is_branch):
            branch_success = (out != Bits(32)(0)) ^ branch_flip
            branch_offset = branch_success.select(imm, Bits(32)(4))

        with Condition(change_PC):
            flush_PC = out & out

        log_parts = ["instruction_addr=0x{:08X}"]
        for i in range(32):
            log_parts.append(f"x{i}=0x{{:08X}}")
        log_format = " ".join(log_parts)
        new_regs = [(rd == Bits(5)(i)).select(data, reg_file.regs[i]) for i in range(32)]
        new_regs[0] = reg_file.regs[0]
        log(log_format, instruction_addr, *new_regs)

        return flush_PC, branch_offset, rd
