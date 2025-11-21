from assassyn.frontend import *
from instruction import MO_LEN, WBF_LEN, MemoryOperation
from reg_file import RegFile, RegOccupation
from utils import Bool, pop_or, to_one_hot


class WriteBack(Module):
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
    def build(self, reg_file: RegFile, dcache: SRAM):
        need_write_back = self.rd.valid()

        instruction_addr = pop_or(self.instruction_addr, Bits(32)(0))
        rd = pop_or(self.rd, Bits(5)(0))
        _ = pop_or(self.rs1, Bits(32)(0))
        _ = pop_or(self.rs2, Bits(32)(0))
        imm = pop_or(self.imm, Bits(32)(0))
        memory_operation = pop_or(self.memory_operation, Bits(MO_LEN)(0))
        is_branch = pop_or(self.is_branch, Bool(0))
        branch_flip = pop_or(self.branch_flip, Bool(0))
        change_PC = pop_or(self.change_PC, Bool(0))
        write_back_from = pop_or(self.write_back_from, Bits(WBF_LEN)(0))
        alu_result = pop_or(self.alu_result, Bits(32)(0))

        data = Bits(32)(0)

        with Condition(need_write_back):
            dout: Value = dcache.dout[0]
            dout_byte = dout[0:7]
            dout_half = dout[0:15]

            load_byte = dout_byte.sext(Bits(32))
            load_half = dout_half.sext(Bits(32))
            load_word = dout
            load_byteu = dout_byte.zext(Bits(32))
            load_halfu = dout_half.zext(Bits(32))

            load = to_one_hot(memory_operation, MO_LEN).select1hot(
                *[load_byte, load_half, load_word, load_byteu, load_halfu, Bits(32)(0), Bits(32)(0), Bits(32)(0)]
            )

            data = to_one_hot(write_back_from, 4).select1hot(*[alu_result, load, instruction_addr + Bits(32)(4), imm])

        reg_file.build(rd, data)

        branch_success = is_branch & ((alu_result != Bits(32)(0)) ^ branch_flip)
        with Condition(branch_success):
            flush_PC = alu_result & alu_result
        with Condition(change_PC):
            PC_adder = imm & imm

        return flush_PC, PC_adder, rd
