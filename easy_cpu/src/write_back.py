from assassyn.frontend import *
from memory import Memory
from reg_file import RegFile
from utils import Bool, pop_or


class WriteBack(Module):
    verbose: bool

    instruction_addr: Port
    rd: Port

    def __init__(self, verbose: bool):
        super().__init__(
            ports={
                "instruction_addr": Port(Bits(32)),
                "rd": Port(Bits(5)),
            }
        )
        self.verbose = verbose

    @module.combinational
    def build(self, reg_file: RegFile, memory: Memory):
        instruction_addr = pop_or(self.instruction_addr, Bits(32)(0))
        rd = pop_or(self.rd, Bits(5)(0))

        out = memory.get_out()

        reg_file.build(rd, out)

        log_parts = ["instruction_addr=0x{:08X}"]
        for i in range(32):
            log_parts.append(f"x{i}=0x{{:08X}}")
        log_format = " ".join(log_parts)
        new_regs = [(rd == Bits(5)(i)).select(out, reg_file.regs[i]) for i in range(32)]
        new_regs[0] = reg_file.regs[0]
        log(log_format, instruction_addr, *new_regs)

        return rd
