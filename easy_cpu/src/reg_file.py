from assassyn.frontend import *
from utils import Bool


class RegOccupation(Downstream):
    occupies: list[Array]

    def __init__(self):
        super().__init__()

        self.occupies = [RegArray(UInt(2), 1) for _ in range(32)]

    @downstream.combinational
    def build(self, occupy_reg: Value, release_reg: Value):
        occupy_reg = occupy_reg.optional(Bits(5)(0))
        release_reg = release_reg.optional(Bits(5)(0))

        with Condition(occupy_reg != release_reg):
            for index in range(1, 32):
                index_value = Bits(5)(index)
                with Condition(occupy_reg == index_value):
                    self.occupies[index][0] += UInt(2)(1)
                with Condition(release_reg == index_value):
                    self.occupies[index][0] -= UInt(2)(1)

    def __getitem__(self, index: Value) -> Value:
        d = {Bits(5)(i): self.occupies[i][0] for i in range(0, 32)}
        d[None] = self.occupies[0][0]
        return index.case(d)  # pyright: ignore[reportArgumentType]


class RegFile(Downstream):
    regs: Array

    rd: Port
    rd_data: Port

    def __init__(self):
        super().__init__()

        self.regs = RegArray(Bits(32), 32)

    @downstream.combinational
    def build(self, rd: Value, rd_data: Value):
        wait_until(rd.valid() & rd_data.valid())

        with Condition(rd != Bits(5)(0)):
            self.regs[rd] = rd_data
