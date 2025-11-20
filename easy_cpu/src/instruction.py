from alu import RV32I_ALU, BitsALU
from assassyn.frontend import Value, Bits, Record

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from utils import Bool


@dataclass
class InstructionArgs:
    rd: Value
    rs1: Value
    rs1_valid: Value
    rs2: Value
    rs2_valid: Value
    imm: Value
    imm_valid: Value
    alu_op: Value
    memory_operation: Value

    is_branch: Value
    branch_flip: Value

    change_PC: Value


def default_instruction_arguments() -> InstructionArgs:
    return InstructionArgs(
        rd=Bits(32)(0),
        rs1=Bits(5)(0),
        rs1_valid=Bool(0),
        rs2=Bits(5)(0),
        rs2_valid=Bool(0),
        imm=Bits(32)(0),
        imm_valid=Bool(0),
        alu_op=BitsALU(0),
        memory_operation=Bits(2)(0),
        is_branch=Bool(0),
        branch_flip=Bool(0),
        change_PC=Bool(0),
    )


class MemoryOperation(Enum):
    NONE = 0
    LOAD = 1
    STORE = 2


@dataclass
class Instruction:
    opcode: int
    funct3: None | int
    funct7: None | int

    alu_op: RV32I_ALU
    has_rd: bool
    has_rs1: bool
    has_rs2: bool
    imm: None | Callable[[Value], Value]

    change_PC: bool

    def matches(self, instruction: Value) -> Value:
        op_match = instruction[0:6] == Bits(7)(self.opcode)
        funct3_match = Bool(1) if self.funct3 is None else instruction[12:14] == Bits(3)(self.funct3)
        funct7_match = Bool(1) if self.funct7 is None else instruction[25:31] == Bits(7)(self.funct7)
        return op_match & funct3_match & funct7_match

    def set_args(self, instruction: Value, args: InstructionArgs) -> InstructionArgs:
        args.alu_op |= self.alu_op
        if self.has_rd:
            args.rd |= instruction[7:11]
        if self.has_rs1:
            args.rs1 |= instruction[15:19]
        if self.has_rs2:
            args.rs2 |= instruction[20:24]
        if self.imm is not None:
            args.imm |= self.imm(instruction)
        if self.change_PC:
            args.change_PC |= Bool(1)

        return args


class RTypeInstruction(Instruction):
    def __init__(self, opcode: int, alu_op: RV32I_ALU, funct3: int, funct7: int):
        super().__init__(
            opcode=opcode,
            alu_op=alu_op,
            funct3=funct3,
            funct7=funct7,
            has_rd=True,
            has_rs1=True,
            has_rs2=True,
            imm=None,
            change_PC=False,
        )


class ITypeInstruction(Instruction):
    is_load: bool

    def __init__(
        self,
        opcode: int,
        alu_op: RV32I_ALU,
        funct3: int,
        funct7: None | int = None,
        change_PC: bool = False,
        is_load: bool = False,
    ):
        def imm_fn(instruction: Value) -> Value:
            return instruction[20:31].sext(Bits(32))

        super().__init__(
            opcode=opcode,
            alu_op=alu_op,
            funct3=funct3,
            funct7=funct7,
            has_rd=True,
            has_rs1=True,
            has_rs2=False,
            imm=imm_fn,
            change_PC=change_PC,
        )
        self.is_load = is_load

    def set_args(self, instruction: Value, args: InstructionArgs) -> InstructionArgs:
        args = super().set_args(instruction, args)
        if self.is_load:
            args.memory_operation |= Bits(2)(MemoryOperation.LOAD.value)
        return args


class STypeInstruction(Instruction):
    def __init__(self, opcode: int, alu_op: RV32I_ALU, funct3: int):
        def imm_fn(instruction: Value) -> Value:
            imm_0_4 = instruction[7:11]
            imm_5_11 = instruction[25:31]
            return (imm_0_4.concat(imm_5_11)).sext(Bits(32))

        super().__init__(
            opcode=opcode,
            alu_op=alu_op,
            funct3=funct3,
            funct7=None,
            has_rd=False,
            has_rs1=True,
            has_rs2=True,
            imm=imm_fn,
            change_PC=False,
        )

    def set_args(self, instruction: Value, args: InstructionArgs) -> InstructionArgs:
        args = super().set_args(instruction, args)
        args.memory_operation |= Bits(2)(MemoryOperation.STORE.value)
        return args


class BTypeInstruction(Instruction):
    branch_flip: bool

    def __init__(self, opcode: int, alu_op: RV32I_ALU, funct3: int, branch_flip: bool = False):
        def imm_fn(instruction: Value) -> Value:
            imm_11 = instruction[7]
            imm_1_4 = instruction[8:11]
            imm_5_10 = instruction[25:30]
            imm_12 = instruction[31]
            return Bool(0).concat(imm_1_4).concat(imm_5_10).concat(imm_11).concat(imm_12).sext(Bits(32))

        super().__init__(
            opcode=opcode,
            alu_op=alu_op,
            funct3=funct3,
            funct7=None,
            has_rd=False,
            has_rs1=True,
            has_rs2=True,
            imm=imm_fn,
            change_PC=True,
        )
        self.branch_flip = branch_flip

    def set_args(self, instruction: Value, args: InstructionArgs) -> InstructionArgs:
        args = super().set_args(instruction, args)
        if self.branch_flip:
            args.branch_flip |= Bool(1)
        args.is_branch |= Bool(1)

        return args


class UTypeInstruction(Instruction):
    def __init__(self, opcode: int, alu_op: RV32I_ALU):
        def imm_fn(instruction: Value) -> Value:
            return Bits(12)(0).concat(instruction[12:31])

        super().__init__(
            opcode=opcode,
            alu_op=alu_op,
            funct3=None,
            funct7=None,
            has_rd=True,
            has_rs1=False,
            has_rs2=False,
            imm=imm_fn,
            change_PC=False,
        )


class JTypeInstruction(Instruction):
    def __init__(self, opcode: int, alu_op: RV32I_ALU):
        def imm_fn(instruction: Value) -> Value:
            imm_1_10 = instruction[21:30]
            imm_11 = instruction[20]
            imm_12_19 = instruction[12:19]
            imm_20 = instruction[31]
            return Bool(0).concat(imm_1_10).concat(imm_11).concat(imm_12_19).concat(imm_20).sext(Bits(32))

        super().__init__(
            opcode=opcode,
            alu_op=alu_op,
            funct3=None,
            funct7=None,
            has_rd=True,
            has_rs1=False,
            has_rs2=False,
            imm=imm_fn,
            change_PC=True,
        )


class Instructions(Enum):
    ADD = RTypeInstruction(opcode=0b0110011, alu_op=RV32I_ALU.ADD, funct3=0x0, funct7=0x00)
    SUB = RTypeInstruction(opcode=0b0110011, alu_op=RV32I_ALU.SUB, funct3=0x0, funct7=0x20)
    XOR = RTypeInstruction(opcode=0b0110011, alu_op=RV32I_ALU.XOR, funct3=0x4, funct7=0x00)
    OR = RTypeInstruction(opcode=0b0110011, alu_op=RV32I_ALU.OR, funct3=0x6, funct7=0x00)
    AND = RTypeInstruction(opcode=0b0110011, alu_op=RV32I_ALU.AND, funct3=0x7, funct7=0x00)
    SLL = RTypeInstruction(opcode=0b0110011, alu_op=RV32I_ALU.SLL, funct3=0x1, funct7=0x00)
    SRL = RTypeInstruction(opcode=0b0110011, alu_op=RV32I_ALU.SRL, funct3=0x5, funct7=0x00)
    SRA = RTypeInstruction(opcode=0b0110011, alu_op=RV32I_ALU.SRA, funct3=0x5, funct7=0x20)
    SLT = RTypeInstruction(opcode=0b0110011, alu_op=RV32I_ALU.SLT, funct3=0x2, funct7=0x00)
    SLTU = RTypeInstruction(opcode=0b0110011, alu_op=RV32I_ALU.SLTU, funct3=0x3, funct7=0x00)

    ADDI = ITypeInstruction(opcode=0b0010011, alu_op=RV32I_ALU.ADD, funct3=0x0)
    XORI = ITypeInstruction(opcode=0b0010011, alu_op=RV32I_ALU.XOR, funct3=0x4)
    ORI = ITypeInstruction(opcode=0b0010011, alu_op=RV32I_ALU.OR, funct3=0x6)
    ANDI = ITypeInstruction(opcode=0b0010011, alu_op=RV32I_ALU.AND, funct3=0x7)
    SLLI = ITypeInstruction(opcode=0b0010011, alu_op=RV32I_ALU.SLL, funct3=0x1, funct7=0x00)
    SRLI = ITypeInstruction(opcode=0b0010011, alu_op=RV32I_ALU.SRL, funct3=0x5, funct7=0x00)
    SRAI = ITypeInstruction(opcode=0b0010011, alu_op=RV32I_ALU.SRA, funct3=0x5, funct7=0x20)
    SLTI = ITypeInstruction(opcode=0b0010011, alu_op=RV32I_ALU.SLT, funct3=0x2)
    SLTIU = ITypeInstruction(opcode=0b0010011, alu_op=RV32I_ALU.SLTU, funct3=0x3)

    LB = ITypeInstruction(opcode=0b0000011, alu_op=RV32I_ALU.ADD, funct3=0x0, is_load=True)
    LH = ITypeInstruction(opcode=0b0000011, alu_op=RV32I_ALU.ADD, funct3=0x1, is_load=True)
    LW = ITypeInstruction(opcode=0b0000011, alu_op=RV32I_ALU.ADD, funct3=0x2, is_load=True)
    LBU = ITypeInstruction(opcode=0b0000011, alu_op=RV32I_ALU.ADD, funct3=0x4, is_load=True)
    LHU = ITypeInstruction(opcode=0b0000011, alu_op=RV32I_ALU.ADD, funct3=0x5, is_load=True)

    SB = STypeInstruction(opcode=0b0100011, alu_op=RV32I_ALU.ADD, funct3=0x0)
    SH = STypeInstruction(opcode=0b0100011, alu_op=RV32I_ALU.ADD, funct3=0x1)
    SW = STypeInstruction(opcode=0b0100011, alu_op=RV32I_ALU.ADD, funct3=0x2)

    # alu 结果非零跳转，全零不跳转
    BNE = BTypeInstruction(opcode=0b1100011, alu_op=RV32I_ALU.SUB, funct3=0x1)
    BLT = BTypeInstruction(opcode=0b1100011, alu_op=RV32I_ALU.SLT, funct3=0x4)
    BLTU = BTypeInstruction(opcode=0b1100011, alu_op=RV32I_ALU.SLTU, funct3=0x6)

    # alu 结果全零跳转，非零不跳转
    BEQ = BTypeInstruction(opcode=0b1100011, alu_op=RV32I_ALU.SUB, funct3=0x0, branch_flip=True)
    BGE = BTypeInstruction(opcode=0b1100011, alu_op=RV32I_ALU.SLT, funct3=0x5, branch_flip=True)
    BGEU = BTypeInstruction(opcode=0b1100011, alu_op=RV32I_ALU.SLTU, funct3=0x7, branch_flip=True)

    JAL = JTypeInstruction(opcode=0b1101111, alu_op=RV32I_ALU.ADD)
    JALR = ITypeInstruction(opcode=0b1100111, funct3=0x0, alu_op=RV32I_ALU.ADD, change_PC=True)

    LUI = UTypeInstruction(opcode=0b0110111, alu_op=RV32I_ALU.ADD)
    AUIPC = UTypeInstruction(opcode=0b0010111, alu_op=RV32I_ALU.ADD)

    EBREAK = ITypeInstruction(opcode=0b1110011, funct3=0x0, alu_op=RV32I_ALU.ADD)
