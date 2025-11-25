from alu import ALU_LEN, BITS_ALU, alu
from assassyn.frontend import *
from bypass import Bypasser
from instruction import MO_LEN, OF_LEN, OperantFrom
from utils import Bool, flush_all_ports, forward_ports, peek_or, pop_or, to_one_hot


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
    is_jalr: Port
    branch_predict: Port

    alu_out: Array

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
                "is_jalr": Port(Bool),
                "branch_predict": Port(Bool),
            }
        )
        self.verbose = verbose
        self.alu_out = RegArray(Bits(32), 1)

    @module.combinational
    def build(self, memory: Module, bypasser: Bypasser):
        bypass_flush_condition = bypasser.should_flush[0]
        with Condition(bypass_flush_condition):
            flush_all_ports(self)

        with Condition(~bypass_flush_condition):
            instruction_addr = self.instruction_addr.peek()

            alu_op = self.alu_op.pop()
            operant1_from = self.operant1_from.pop()
            operant2_from = self.operant2_from.pop()

            rs1 = peek_or(self.rs1, Bits(32)(0))
            rs2 = peek_or(self.rs2, Bits(32)(0))
            imm = pop_or(self.imm, Bits(32)(0))

            one_hot_operant1_from = to_one_hot(operant1_from, len(OperantFrom))
            one_hot_operant2_from = to_one_hot(operant2_from, len(OperantFrom))
            operants = [rs1, rs2, imm, instruction_addr, Bits(32)(4)]
            operant1 = one_hot_operant1_from.select1hot(*operants)
            operant2 = one_hot_operant2_from.select1hot(*operants)
            alu_result = alu(to_one_hot(alu_op, ALU_LEN), operant1, operant2)

            self.alu_out[0] = alu_result

            memory.bind(alu_result=alu_result)

            if self.verbose:
                log(
                    "instruction_addr: 0x{:08X}, operant1: 0x{:08X}, operant2: 0x{:08X}, result: 0x{:08X}, rs1: 0x{:08X}, rs2: 0x{:08X}, operant1_from: {}, operant2_from: {}",
                    instruction_addr,
                    operant1,
                    operant2,
                    alu_result,
                    rs1,
                    rs2,
                    operant1_from,
                    operant2_from,
                )

            with Condition(~self.memory_operation.valid()):
                rd = peek_or(self.rd, Bits(5)(0))

            is_branch = pop_or(self.is_branch, Bool(0))
            branch_flip = pop_or(self.branch_flip, Bool(0))
            change_PC = pop_or(self.change_PC, Bool(0))
            is_jalr = pop_or(self.is_jalr, Bool(0))
            branch_predict = pop_or(self.branch_predict, Bool(0))

            branch_success = (alu_result != Bits(32)(0)) ^ branch_flip
            mis_predict = is_branch & (branch_predict ^ branch_success)
            with Condition(mis_predict | change_PC):
                flush_PC = is_jalr.select(rs1, instruction_addr)

                branch_offset = (change_PC | branch_success).select(imm, Bits(32)(4))

            forward_ports(
                memory,
                [
                    self.instruction_addr,
                    self.rd,
                    self.rs1,
                    self.rs2,
                    self.memory_operation,
                ],
            )

            memory.async_called()

        return flush_PC, branch_offset, rd

    def get_out(self) -> Value:
        return self.alu_out[0]
