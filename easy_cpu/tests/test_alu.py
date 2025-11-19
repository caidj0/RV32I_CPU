from assassyn.frontend import *
from assassyn.backend import elaborate
from assassyn.utils import run_simulator
from alu import *
from utils import run_quietly

Instructions = [
    # 基本算术运算
    (10, 15, RV32I_ALU.ADD),  # 10 + 15 = 25
    (100, 75, RV32I_ALU.SUB),  # 100 - 75 = 25
    (0xFFFFFFFF, 1, RV32I_ALU.ADD),  # 溢出测试: -1 + 1 = 0
    (0, 1, RV32I_ALU.SUB),  # 下溢测试: 0 - 1 = 0xFFFFFFFF
    # 移位运算
    (0b1010, 2, RV32I_ALU.SLL),  # 逻辑左移: 1010 << 2 = 101000
    (0x80000000, 1, RV32I_ALU.SRL),  # 逻辑右移: 最高位右移
    (0x80000000, 1, RV32I_ALU.SRA),  # 算术右移: 保留符号位
    (0xFFFFFFFF, 4, RV32I_ALU.SRA),  # 算术右移: -1 >> 4 = -1
    (0x12345678, 8, RV32I_ALU.SRL),  # 逻辑右移
    # 比较运算
    (5, 10, RV32I_ALU.SLT),  # 有符号比较: 5 < 10 = 1
    (10, 5, RV32I_ALU.SLT),  # 有符号比较: 10 < 5 = 0
    (0xFFFFFFFF, 1, RV32I_ALU.SLT),  # 有符号比较: -1 < 1 = 1
    (0xFFFFFFFF, 1, RV32I_ALU.SLTU),  # 无符号比较: 0xFFFFFFFF < 1 = 0
    (5, 10, RV32I_ALU.SLTU),  # 无符号比较: 5 < 10 = 1
    # 逻辑运算
    (0xAAAA5555, 0x5555AAAA, RV32I_ALU.XOR),  # 异或
    (0xF0F0F0F0, 0x0F0F0F0F, RV32I_ALU.OR),  # 或
    (0xFFFF0000, 0xFF00FF00, RV32I_ALU.AND),  # 与
    (0xFFFFFFFF, 0xFFFFFFFF, RV32I_ALU.AND),  # 全1与
    (0, 0, RV32I_ALU.OR),  # 全0或
    (0xFFFFFFFF, 0, RV32I_ALU.XOR),  # 异或取反
]


def check(raw: str):
    lines = raw.splitlines()
    for index, line in enumerate(lines):
        num = int(line.split()[-1])
        num1, num2, op = Instructions[index]
        shifter = num2 & 0b11111
        target: int

        # 将无符号整数转换为有符号整数的辅助函数
        def to_signed(val):
            val = val & 0xFFFFFFFF  # 确保是32位
            if val & 0x80000000:  # 如果最高位是1，表示负数
                return val - 0x100000000
            return val

        match op:
            case RV32I_ALU.ADD:
                target = (num1 + num2) & 0xFFFFFFFF
            case RV32I_ALU.SUB:
                target = (num1 - num2) & 0xFFFFFFFF
            case RV32I_ALU.SLL:
                target = (num1 << shifter) & 0xFFFFFFFF
            case RV32I_ALU.SLT:
                target = 1 if to_signed(num1) < to_signed(num2) else 0
            case RV32I_ALU.SLTU:
                target = 1 if num1 < num2 else 0
            case RV32I_ALU.XOR:
                target = (num1 ^ num2) & 0xFFFFFFFF
            case RV32I_ALU.SRA:
                # 算术右移，需要保留符号位
                signed_val = to_signed(num1)
                target = (signed_val >> shifter) & 0xFFFFFFFF
            case RV32I_ALU.SRL:
                # 逻辑右移
                target = (num1 >> shifter) & 0xFFFFFFFF
            case RV32I_ALU.OR:
                target = (num1 | num2) & 0xFFFFFFFF
            case RV32I_ALU.AND:
                target = (num1 & num2) & 0xFFFFFFFF

        assert num == target, f"Line {index}: expected {target}, got {num}"


class Driver(Module):
    reg: Array
    operant1_data: Array
    operant2_data: Array
    op_data: Array

    def __init__(self):
        super().__init__(ports={})
        self.reg = RegArray(UInt(8), 1)
        self.operant1_data = RegArray(Bits(32), len(Instructions), [x[0] for x in Instructions])
        self.operant2_data = RegArray(Bits(32), len(Instructions), [x[1] for x in Instructions])
        self.op_data = RegArray(
            BitsALU,
            len(Instructions),
            [1 << x[2].value for x in Instructions],
        )

    @module.combinational
    def build(self):
        op = self.op_data[self.reg[0]]
        operant1 = self.operant1_data[self.reg[0]]
        operant2 = self.operant2_data[self.reg[0]]

        new_reg = self.reg[0] + UInt(8)(1)
        new_reg = (new_reg >= UInt(8)(len(Instructions))).select(UInt(8)(0), new_reg)
        self.reg[0] = new_reg

        log("{}", alu(op, operant1, operant2))


def test_alu():
    sys = SysBuilder("alu_test")
    with sys:
        driver = Driver()
        driver.build()

    sim, _ = elaborate(sys, verbose=False, sim_threshold=len(Instructions))

    raw, stdout, stderr = run_quietly(run_simulator, sim)
    assert raw is not None, stderr
    check(raw)
