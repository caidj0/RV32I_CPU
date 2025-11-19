from assassyn.frontend import *
from assassyn.backend import elaborate
from assassyn.utils import run_simulator

from reg_file import RegFile, RegOccupation

# 测试指令: (rd, rd_data)
Instructions = [
    # 基本写入测试
    (1, 0x12345678),  # 写入寄存器 x1
    (2, 0xABCDEF00),  # 写入寄存器 x2
    (3, 0xFFFFFFFF),  # 写入寄存器 x3 (全1)
    (4, 0x00000000),  # 写入寄存器 x4 (全0)
    (5, 0x80000000),  # 写入寄存器 x5 (最高位为1)
    # 覆盖写入测试
    (1, 0x11111111),  # 覆盖写入 x1
    (2, 0x22222222),  # 覆盖写入 x2
    # 边界寄存器测试
    (31, 0xDEADBEEF),  # 写入最后一个寄存器 x31
    (30, 0xCAFEBABE),  # 写入 x30
    # x0 寄存器测试 (应该保持为0)
    (0, 0xFFFFFFFF),  # 尝试写入 x0 (应该被忽略)
    (0, 0x12345678),  # 再次尝试写入 x0 (应该被忽略)
    # 混合写入测试
    (10, 0x10101010),  # 写入 x10
    (11, 0x01010101),  # 写入 x11
    (12, 0xF0F0F0F0),  # 写入 x12
    (13, 0x0F0F0F0F),  # 写入 x13
]


def check(raw: str):
    lines = raw.splitlines()

    # 初始化期望的寄存器状态
    expected_regs = [0] * 32

    for index, line in enumerate(lines):
        # 解析输出的寄存器值 (格式: "x0=0x00000000 x1=0x12345678 ...")
        regs = {}
        parts = line.split()
        for part in parts:
            if "=" in part:
                reg_name, value = part.split("=")
                reg_num = int(reg_name[1:])  # 去掉 'x' 前缀
                reg_value = int(value, 16)
                regs[reg_num] = reg_value

        # 验证所有寄存器（当前周期查看的是上一个周期写入的结果）
        for reg_num in range(32):
            expected = expected_regs[reg_num]
            actual = regs.get(reg_num, 0)
            assert (
                actual == expected
            ), f"Cycle {index}, Register x{reg_num}: expected 0x{expected:08X}, got 0x{actual:08X}"

        print(f"✓ Cycle {index}: All registers match expected values")

        # 更新期望的寄存器状态（本周期的写入会在下一个周期可见）
        if index < len(Instructions):
            rd, rd_data = Instructions[index]
            if rd != 0:  # x0 永远为 0
                expected_regs[rd] = rd_data & 0xFFFFFFFF


class Driver(Module):
    cycle: Array
    rd_data_array: Array
    rd_array: Array
    regs: Array

    def __init__(self):
        super().__init__(ports={})
        self.cycle = RegArray(UInt(8), 1)
        self.rd_data_array = RegArray(Bits(32), len(Instructions), [x[1] for x in Instructions])
        self.rd_array = RegArray(Bits(5), len(Instructions), [x[0] for x in Instructions])
        # 寄存器文件: 32个32位寄存器
        self.regs = RegArray(Bits(32), 32)

    @module.combinational
    def build(self, reg_file: RegFile):
        # 获取当前周期的写入信号
        rd = self.rd_array[self.cycle[0]]
        rd_data = self.rd_data_array[self.cycle[0]]

        new_cycle = self.cycle[0] + UInt(8)(1)
        self.cycle[0] = (new_cycle < UInt(8)(len(Instructions))).select(new_cycle, UInt(8)(0))

        # 打印所有寄存器的值
        log_parts = []
        for i in range(32):
            log_parts.append(f"x{i}={{:08X}}")
        log_format = " ".join(log_parts)
        log(log_format, *[reg_file.regs[i] for i in range(32)])

        return rd, rd_data


def test_reg_file():
    sys = SysBuilder("reg_file_test")
    with sys:
        driver = Driver()
        reg_file = RegFile()
        rd, rd_data = driver.build(reg_file)
        reg_file.build(rd, rd_data)

    sim, _ = elaborate(sys, sim_threshold=len(Instructions) + 1)

    raw = run_simulator(sim)
    print(raw)
    check(raw)


if __name__ == "__main__":
    test_reg_file()
