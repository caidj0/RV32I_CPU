from math import ceil, log2
from pickletools import OpcodeInfo
from alu import RV32I_ALU, BITS_ALU
from assassyn.frontend import Value, Bits, Record

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Callable

from utils import Bool, RecodeWrapper, ValueWrapper, sext


class MemoryOperation(Enum):
    LOAD_BYTE = 0
    LOAD_HALF = 1
    LOAD_WORD = 2
    LOAD_BYTEU = 3
    LOAD_HALFU = 4
    STORE_BYTE = 5
    STORE_HALF = 6
    STORE_WORD = 7


MO_LEN = ceil(log2(len(MemoryOperation)))


class OperantFrom(Enum):
    RS1 = 0
    RS2 = 1
    IMM = 2
    PC = 3


OF_LEN = ceil(log2(len(OperantFrom)))


class WriteBackFrom(Enum):
    OUT = 0
    INC_PC = 1


WBF_LEN = ceil(log2(len(WriteBackFrom)))


@dataclass
class InstructionArgs(RecodeWrapper):
    rd: ValueWrapper
    rs1: ValueWrapper
    rs2: ValueWrapper
    imm: ValueWrapper

    alu_op: ValueWrapper
    operant1_from: ValueWrapper
    operant2_from: ValueWrapper

    memory_operation: ValueWrapper
    is_branch: ValueWrapper
    branch_flip: ValueWrapper
    change_PC: ValueWrapper
    just_stall: ValueWrapper

    write_back_from: ValueWrapper


def default_instruction_arguments() -> InstructionArgs:
    return InstructionArgs(
        rd=ValueWrapper(Bits(5), False),
        rs1=ValueWrapper(Bits(5), False),
        rs2=ValueWrapper(Bits(5), False),
        imm=ValueWrapper(Bits(32), False),
        alu_op=ValueWrapper(BITS_ALU, False),
        operant1_from=ValueWrapper(Bits(OF_LEN), False),
        operant2_from=ValueWrapper(Bits(OF_LEN), False),
        memory_operation=ValueWrapper(Bits(MO_LEN), False),
        is_branch=ValueWrapper(Bool, True),
        branch_flip=ValueWrapper(Bool, True),
        change_PC=ValueWrapper(Bool, True),
        just_stall=ValueWrapper(Bool, True),
        write_back_from=ValueWrapper(Bits(WBF_LEN), False),
    )


@dataclass
class ALUInfo:
    alu_op: RV32I_ALU
    operant1_from: OperantFrom
    operant2_from: OperantFrom


@dataclass
class Instruction:
    opcode: int
    funct3: None | int
    funct7: None | int

    alu_info: None | ALUInfo

    has_rd: bool
    has_rs1: bool
    has_rs2: bool
    imm: None | Callable[[Value], Value]

    change_PC: bool

    write_back_from: None | WriteBackFrom

    def matches(self, instruction: Value) -> Value:
        op_match = instruction[0:6] == Bits(7)(self.opcode)
        funct3_match = Bool(1) if self.funct3 is None else instruction[12:14] == Bits(3)(self.funct3)
        funct7_match = Bool(1) if self.funct7 is None else instruction[25:31] == Bits(7)(self.funct7)
        return op_match & funct3_match & funct7_match

    def select_args(self, cond: Value, instruction: Value, args: InstructionArgs) -> InstructionArgs:

        if self.alu_info is not None:
            args.alu_op.select(cond, BITS_ALU(self.alu_info.alu_op.value))
            args.operant1_from.select(cond, Bits(OF_LEN)(self.alu_info.operant1_from.value))
            args.operant2_from.select(cond, Bits(OF_LEN)(self.alu_info.operant2_from.value))

        if self.has_rd:
            args.rd.select(cond, instruction[7:11])
        if self.has_rs1:
            args.rs1.select(cond, instruction[15:19])
        if self.has_rs2:
            args.rs2.select(cond, instruction[20:24])
        if self.imm is not None:
            args.imm.select(cond, self.imm(instruction))
        if self.change_PC:
            args.change_PC.select(cond, Bool(1))
        if self.write_back_from is not None:
            args.write_back_from.select(cond, Bits(WBF_LEN)(self.write_back_from.value))

        return args


class RTypeInstruction(Instruction):
    def __init__(self, opcode: int, alu_op: RV32I_ALU, funct3: int, funct7: int):
        super().__init__(
            opcode=opcode,
            alu_info=ALUInfo(alu_op, OperantFrom.RS1, OperantFrom.RS2),
            funct3=funct3,
            funct7=funct7,
            has_rd=True,
            has_rs1=True,
            has_rs2=True,
            imm=None,
            change_PC=False,
            write_back_from=WriteBackFrom.OUT,
        )


class ITypeInstruction(Instruction):
    memory_operation: None | MemoryOperation
    just_stall: bool

    def __init__(
        self,
        opcode: int,
        alu_op: None | RV32I_ALU,
        funct3: int,
        funct7: None | int = None,
        change_PC: bool = False,
        memory_operation: None | MemoryOperation = None,
        write_back_from: None | WriteBackFrom = WriteBackFrom.OUT,
        just_stall: bool = False,
    ):
        def imm_fn(instruction: Value) -> Value:
            return sext(instruction[20:31], Bits(32))

        super().__init__(
            opcode=opcode,
            alu_info=ALUInfo(alu_op, OperantFrom.RS1, OperantFrom.IMM) if alu_op is not None else None,
            funct3=funct3,
            funct7=funct7,
            has_rd=True,
            has_rs1=True,
            has_rs2=False,
            imm=imm_fn,
            change_PC=change_PC,
            write_back_from=write_back_from,
        )
        self.memory_operation = memory_operation
        self.just_stall = just_stall

    def select_args(self, cond: Value, instruction: Value, args: InstructionArgs) -> InstructionArgs:
        args = super().select_args(cond, instruction, args)
        if self.memory_operation is not None:
            args.memory_operation.select(cond, Bits(MO_LEN)(self.memory_operation.value))
        if self.just_stall:
            args.just_stall.select(cond, Bool(1))
        return args


class STypeInstruction(Instruction):
    memory_operation: MemoryOperation

    def __init__(self, opcode: int, alu_op: RV32I_ALU, funct3: int, memory_operation: MemoryOperation):
        def imm_fn(instruction: Value) -> Value:
            imm_4_0 = instruction[7:11]
            imm_11_5 = instruction[25:31]
            return sext(imm_11_5.concat(imm_4_0), Bits(32))

        super().__init__(
            opcode=opcode,
            alu_info=ALUInfo(alu_op, OperantFrom.RS1, OperantFrom.IMM),
            funct3=funct3,
            funct7=None,
            has_rd=False,
            has_rs1=True,
            has_rs2=True,
            imm=imm_fn,
            change_PC=False,
            write_back_from=None,
        )
        self.memory_operation = memory_operation

    def select_args(self, cond: Value, instruction: Value, args: InstructionArgs) -> InstructionArgs:
        args = super().select_args(cond, instruction, args)
        args.memory_operation.select(cond, Bits(MO_LEN)(self.memory_operation.value))
        return args


class BTypeInstruction(Instruction):
    branch_flip: bool

    def __init__(self, opcode: int, alu_op: RV32I_ALU, funct3: int, branch_flip: bool = False):
        def imm_fn(instruction: Value) -> Value:
            imm_11 = instruction[7:7]
            imm_4_1 = instruction[8:11]
            imm_10_5 = instruction[25:30]
            imm_12 = instruction[31:31]
            return sext(imm_12.concat(imm_11).concat(imm_10_5).concat(imm_4_1).concat(Bits(1)(0)), Bits(32))

        super().__init__(
            opcode=opcode,
            alu_info=ALUInfo(alu_op, OperantFrom.RS1, OperantFrom.RS2),
            funct3=funct3,
            funct7=None,
            has_rd=False,
            has_rs1=True,
            has_rs2=True,
            imm=imm_fn,
            change_PC=False,
            write_back_from=None,
        )
        self.branch_flip = branch_flip

    def select_args(self, cond: Value, instruction: Value, args: InstructionArgs) -> InstructionArgs:
        args = super().select_args(cond, instruction, args)
        if self.branch_flip:
            args.branch_flip.select(cond, Bool(1))
        args.is_branch.select(cond, Bool(1))

        return args


class UTypeInstruction(Instruction):
    def __init__(
        self,
        opcode: int,
        alu_op: RV32I_ALU,
        operant1_from: OperantFrom,
        operant2_from: OperantFrom,
        write_back_from: WriteBackFrom,
    ):
        def imm_fn(instruction: Value) -> Value:
            return instruction[12:31].concat(Bits(12)(0))

        super().__init__(
            opcode=opcode,
            alu_info=ALUInfo(alu_op, operant1_from, operant2_from),
            funct3=None,
            funct7=None,
            has_rd=True,
            has_rs1=False,
            has_rs2=False,
            imm=imm_fn,
            change_PC=False,
            write_back_from=write_back_from,
        )


class JTypeInstruction(Instruction):
    def __init__(self, opcode: int, alu_op: RV32I_ALU):
        def imm_fn(instruction: Value) -> Value:
            imm_19_12 = instruction[12:19]
            imm_11 = instruction[20:20]
            imm_10_1 = instruction[21:30]
            imm_20 = instruction[31:31]
            return sext(imm_20.concat(imm_19_12).concat(imm_11).concat(imm_10_1).concat(Bits(1)(0)), Bits(32))

        super().__init__(
            opcode=opcode,
            alu_info=ALUInfo(alu_op, OperantFrom.PC, OperantFrom.IMM),
            funct3=None,
            funct7=None,
            has_rd=True,
            has_rs1=False,
            has_rs2=False,
            imm=imm_fn,
            change_PC=True,
            write_back_from=WriteBackFrom.INC_PC,
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

    LB = ITypeInstruction(
        opcode=0b0000011,
        alu_op=RV32I_ALU.ADD,
        funct3=0x0,
        memory_operation=MemoryOperation.LOAD_BYTE,
        write_back_from=WriteBackFrom.OUT,
    )
    LH = ITypeInstruction(
        opcode=0b0000011,
        alu_op=RV32I_ALU.ADD,
        funct3=0x1,
        memory_operation=MemoryOperation.LOAD_HALF,
        write_back_from=WriteBackFrom.OUT,
    )
    LW = ITypeInstruction(
        opcode=0b0000011,
        alu_op=RV32I_ALU.ADD,
        funct3=0x2,
        memory_operation=MemoryOperation.LOAD_WORD,
        write_back_from=WriteBackFrom.OUT,
    )
    LBU = ITypeInstruction(
        opcode=0b0000011,
        alu_op=RV32I_ALU.ADD,
        funct3=0x4,
        memory_operation=MemoryOperation.LOAD_BYTE,
        write_back_from=WriteBackFrom.OUT,
    )
    LHU = ITypeInstruction(
        opcode=0b0000011,
        alu_op=RV32I_ALU.ADD,
        funct3=0x5,
        memory_operation=MemoryOperation.LOAD_HALFU,
        write_back_from=WriteBackFrom.OUT,
    )

    SB = STypeInstruction(
        opcode=0b0100011, alu_op=RV32I_ALU.ADD, funct3=0x0, memory_operation=MemoryOperation.STORE_BYTE
    )
    SH = STypeInstruction(
        opcode=0b0100011, alu_op=RV32I_ALU.ADD, funct3=0x1, memory_operation=MemoryOperation.STORE_HALF
    )
    SW = STypeInstruction(
        opcode=0b0100011, alu_op=RV32I_ALU.ADD, funct3=0x2, memory_operation=MemoryOperation.STORE_WORD
    )

    # alu 结果非零跳转，全零不跳转
    BNE = BTypeInstruction(opcode=0b1100011, alu_op=RV32I_ALU.SUB, funct3=0x1)
    BLT = BTypeInstruction(opcode=0b1100011, alu_op=RV32I_ALU.SLT, funct3=0x4)
    BLTU = BTypeInstruction(opcode=0b1100011, alu_op=RV32I_ALU.SLTU, funct3=0x6)

    # alu 结果全零跳转，非零不跳转
    BEQ = BTypeInstruction(opcode=0b1100011, alu_op=RV32I_ALU.SUB, funct3=0x0, branch_flip=True)
    BGE = BTypeInstruction(opcode=0b1100011, alu_op=RV32I_ALU.SLT, funct3=0x5, branch_flip=True)
    BGEU = BTypeInstruction(opcode=0b1100011, alu_op=RV32I_ALU.SLTU, funct3=0x7, branch_flip=True)

    JAL = JTypeInstruction(opcode=0b1101111, alu_op=RV32I_ALU.ADD)
    JALR = ITypeInstruction(
        opcode=0b1100111, funct3=0x0, alu_op=RV32I_ALU.ADD, change_PC=True, write_back_from=WriteBackFrom.INC_PC
    )

    LUI = UTypeInstruction(
        opcode=0b0110111,
        alu_op=RV32I_ALU.OR,
        operant1_from=OperantFrom.IMM,
        operant2_from=OperantFrom.IMM,
        write_back_from=WriteBackFrom.OUT,
    )
    AUIPC = UTypeInstruction(
        opcode=0b0010111,
        alu_op=RV32I_ALU.ADD,
        operant1_from=OperantFrom.PC,
        operant2_from=OperantFrom.IMM,
        write_back_from=WriteBackFrom.OUT,
    )

    EBREAK = ITypeInstruction(opcode=0b1110011, funct3=0x0, alu_op=RV32I_ALU.ADD, write_back_from=None, just_stall=True)
