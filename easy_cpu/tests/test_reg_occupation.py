from assassyn.frontend import *
from assassyn.backend import elaborate
from assassyn.utils import run_simulator

from reg_file import RegOccupation

# 测试指令: (occupy_reg, release_reg, expected_changes)
# expected_changes: 一个字典，表示预期的寄存器占用变化
Instructions = [
    # 基本占用测试
    (1, 0, {1: 1}),  # 占用 x1，计数 +1
    (2, 0, {2: 1}),  # 占用 x2，计数 +1
    (3, 0, {3: 1}),  # 占用 x3，计数 +1
    
    # 基本释放测试
    (0, 1, {1: 0}),  # 释放 x1，计数 -1 回到 0
    (0, 2, {2: 0}),  # 释放 x2，计数 -1 回到 0
    
    # 多次占用同一寄存器
    (5, 0, {5: 1}),  # 占用 x5，计数 +1
    (5, 0, {5: 2}),  # 再次占用 x5，计数 +1 到 2
    (5, 0, {5: 3}),  # 再次占用 x5，计数 +1 到 3
    
    # 逐步释放
    (0, 5, {5: 2}),  # 释放 x5，计数 -1 到 2
    (0, 5, {5: 1}),  # 释放 x5，计数 -1 到 1
    (0, 5, {5: 0}),  # 释放 x5，计数 -1 到 0
    
    # 同时占用和释放不同寄存器
    (10, 3, {10: 1, 3: 0}),  # 占用 x10，释放 x3
    (11, 10, {11: 1, 10: 0}),  # 占用 x11，释放 x10
    
    # 同时占用和释放同一寄存器（应该不改变）
    (7, 7, {}),  # x7 占用和释放，计数不变
    
    # 边界寄存器测试
    (31, 0, {31: 1}),  # 占用 x31
    (30, 0, {30: 1}),  # 占用 x30
    (0, 31, {31: 0}),  # 释放 x31
    (0, 30, {30: 0}),  # 释放 x30
    
    # x0 寄存器测试（应该始终保持为0，不受影响）
    (0, 0, {}),  # 占用和释放 x0（无效操作）
    
    # 复杂场景
    (15, 11, {15: 1, 11: 0}),  # 占用 x15，释放 x11
]


def check(raw: str):
    lines = raw.splitlines()
    
    # 初始化期望的寄存器占用状态
    expected_occupies = [0] * 32
    
    for index, line in enumerate(lines):
        # 解析输出的占用状态 (格式: "x0=0 x1=1 x2=0 ...")
        occupies = {}
        parts = line.split()
        for part in parts:
            if "=" in part:
                reg_name, value = part.split("=")
                reg_num = int(reg_name[1:])  # 去掉 'x' 前缀
                occupy_count = int(value)
                occupies[reg_num] = occupy_count
        
        # 验证所有寄存器占用状态（当前周期查看的是上一个周期操作的结果）
        for reg_num in range(32):
            expected = expected_occupies[reg_num]
            actual = occupies.get(reg_num, 0)
            assert (
                actual == expected
            ), f"Cycle {index}, Register x{reg_num}: expected occupation={expected}, got {actual}"
        
        print(f"✓ Cycle {index}: All register occupations match expected values")
        
        # 更新期望的占用状态（本周期的操作会在下一个周期可见）
        if index < len(Instructions):
            occupy_reg, release_reg, expected_changes = Instructions[index]
            
            # 应用预期的变化
            for reg, new_count in expected_changes.items():
                expected_occupies[reg] = new_count


class Driver(Module):
    cycle: Array
    occupy_reg_array: Array
    release_reg_array: Array

    def __init__(self):
        super().__init__(ports={})
        self.cycle = RegArray(UInt(8), 1)
        self.occupy_reg_array = RegArray(
            Bits(5), len(Instructions), [x[0] for x in Instructions]
        )
        self.release_reg_array = RegArray(
            Bits(5), len(Instructions), [x[1] for x in Instructions]
        )

    @module.combinational
    def build(self, reg_occupation: RegOccupation):
        # 获取当前周期的操作
        occupy_reg = self.occupy_reg_array[self.cycle[0]]
        release_reg = self.release_reg_array[self.cycle[0]]

        new_cycle = self.cycle[0] + UInt(8)(1)
        self.cycle[0] = (new_cycle < UInt(8)(len(Instructions))).select(
            new_cycle, UInt(8)(0)
        )

        # 打印所有寄存器的占用状态
        log_parts = []
        for i in range(32):
            log_parts.append(f"x{i}={{}}")
        log_format = " ".join(log_parts)
        log(log_format, *[reg_occupation.occupies[i][0] for i in range(32)])

        return occupy_reg, release_reg


def test_reg_occupation():
    sys = SysBuilder("reg_occupation_test")
    with sys:
        driver = Driver()
        reg_occupation = RegOccupation()
        occupy_reg, release_reg = driver.build(reg_occupation)
        reg_occupation.build(occupy_reg, release_reg)

    sim, _ = elaborate(sys, sim_threshold=len(Instructions) + 1)

    raw = run_simulator(sim)
    print(raw)
    check(raw)


if __name__ == "__main__":
    test_reg_occupation()
