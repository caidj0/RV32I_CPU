from assassyn.frontend import *
from utils import Bool


class RegOccupation(Downstream):
    verbose: bool

    occupies: list[Array]

    def __init__(self, verbose: bool):
        super().__init__()

        self.verbose = verbose

        self.occupies = [RegArray(UInt(2), 1) for _ in range(32)]

    @downstream.combinational
    def build(self, occupy_reg: Value, release_reg: Value, flush_flag: Value | None):
        flush: Value
        if flush_flag:
            flush = flush_flag.valid()
        else:
            flush = Bool(0)

        occupy_reg = flush.select(Bits(5)(0), occupy_reg.optional(Bits(5)(0)))
        release_reg = release_reg.optional(Bits(5)(0))

        with Condition(occupy_reg != release_reg):
            for index in range(1, 32):
                index_value = Bits(5)(index)
                with Condition(occupy_reg == index_value):
                    self.occupies[index][0] += UInt(2)(1)
                with Condition(release_reg == index_value):
                    self.occupies[index][0] -= UInt(2)(1)

        if self.verbose:
            log_parts = ["occupy: {}, release: {},"]
            for i in range(32):
                log_parts.append(f"x{i}={{}}")
            log_format = " ".join(log_parts)
            new_regs = [
                (occupy_reg == Bits(5)(i)).select(
                    (release_reg == Bits(5)(i)).select(self.occupies[i][0], self.occupies[i][0] + UInt(2)(1)),
                    (release_reg == Bits(5)(i)).select(self.occupies[i][0] - UInt(2)(1), self.occupies[i][0]),
                )
                for i in range(32)
            ]
            log(log_format, occupy_reg, release_reg, *new_regs)

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
