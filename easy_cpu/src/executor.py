from alu import ALU_LEN, RV32I_ALU, BITS_ALU, alu
from assassyn.frontend import *
from assassyn.ir.dtype import RecordValue
from instruction import MO_LEN, OF_LEN, WBF_LEN, OperantFrom
from reg_file import RegFile
from utils import Bool, forward_ports, peek_or, to_one_hot


class Executor(Module):
    verbose: bool

    instruction_addr: Port

    rd: Port
    rs1: Port
    rs2: Port
    imm: Port
    alu_op: Port
    operant1_from: Port
    operant2_from: Port
    memory_operation: Port
    is_branch: Port
    branch_flip: Port
    change_PC: Port
    write_back_from: Port

    def __init__(self, verbose: bool):
        super().__init__(
            ports={
                "instruction_addr": Port(Bits(32)),
                "rd": Port(Bits(5)),
                "rs1": Port(Bits(32)),
                "rs2": Port(Bits(32)),
                "imm": Port(Bits(32)),
                "alu_op": Port(BITS_ALU),
                "operant1_from": Port(Bits(OF_LEN)),
                "operant2_from": Port(Bits(OF_LEN)),
                "memory_operation": Port(Bits(MO_LEN)),
                "is_branch": Port(Bool),
                "branch_flip": Port(Bool),
                "change_PC": Port(Bool),
                "write_back_from": Port(Bits(WBF_LEN)),
            }
        )
        self.verbose = verbose

    @module.combinational
    def build(self, memory: Module):

        instruction_addr = self.instruction_addr.peek()

        need_alu = self.alu_op.valid()
        with Condition(need_alu):
            alu_op = self.alu_op.pop()
            operant1_from = self.operant1_from.pop()
            operant2_from = self.operant2_from.pop()

            rs1 = peek_or(self.rs1, Bits(32)(0))
            rs2 = peek_or(self.rs2, Bits(32)(0))
            imm = peek_or(self.imm, Bits(32)(0))

            one_hot_operant1_from = to_one_hot(operant1_from, len(OperantFrom))
            one_hot_operant2_from = to_one_hot(operant2_from, len(OperantFrom))
            operants = [rs1, rs2, imm, instruction_addr]
            operant1 = one_hot_operant1_from.select1hot(*operants)
            operant2 = one_hot_operant2_from.select1hot(*operants)
            alu_result = alu(to_one_hot(alu_op, ALU_LEN), operant1, operant2)

            memory.bind(alu_result=alu_result)

            if self.verbose:
                log(
                    "instruction_addr: 0x{:08X}, operant1: 0x{:08X}, operant2: 0x{:08X}, result: 0x{:08X}, rs1: 0x{:08X}, rs2: 0x{:08X}",
                    instruction_addr,
                    operant1,
                    operant2,
                    alu_result,
                    rs1,
                    rs2,
                )

        forward_ports(
            memory,
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
            ],
        )

        memory.async_called()
