from assassyn.frontend import *
from decoder import Decoder
from utils import Bool


class Fetcher(Module):
    PC: Array

    def __init__(self):
        super().__init__(ports={})
        self.PC = RegArray(Bits(32), 1)

    @module.combinational
    def build(self):
        return self.PC


class FetcherImpl(Downstream):
    stalled: Array
    pushed: Array

    def __init__(self):
        super().__init__()

    # 设计接口时需要小心：如果它的上游均没有运行（即均触发了 wait_until），则下游根本不会运行
    @downstream.combinational
    def build(
        self,
        PC: Array,
        success_decode: Value,
        should_stall: Value,
        flush_PC: Value,
        PC_adder: Value,
        decoder: Decoder,
        icache: SRAM,
    ):
        should_stall = should_stall.optional(Bool(1))
        success_decode = success_decode.optional(Bool(0))

        assume(~(flush_PC.valid() & PC_adder.valid()))
        assume(~((flush_PC.valid() | PC_adder.valid()) & should_stall))

        added_PC = PC[0] + PC_adder.optional(Bits(32)(4))

        new_stalled = (self.stalled[0] | should_stall) & ~(flush_PC.valid() | PC_adder.valid())

        new_PC = flush_PC.optional((~new_stalled & success_decode).select(added_PC, PC[0]))

        icache.build(we=Bool(0), re=Bool(1), addr=new_PC, wdata=Bits(32)(0))
        PC[0] = new_PC
        self.stalled[0] = new_stalled

        with Condition(~new_stalled):
            decoder.bind(instruction_addr=new_PC)
