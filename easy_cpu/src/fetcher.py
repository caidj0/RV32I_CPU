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
        return self.PC, self.PC[0]


class FetcherImpl(Downstream):
    verbose: bool

    stalled: Array

    def __init__(self, verbose: bool):
        super().__init__()
        self.stalled = RegArray(Bool, 1)
        self.verbose = verbose

    # 设计接口时需要小心：如果它的上游均没有运行（即均触发了 wait_until），则下游根本不会运行；并且只会检查 Value 所在的上游，不会检查 array 所在的上游
    @downstream.combinational
    def build(
        self,
        PC_reg: Array,
        PC_addr: Value,
        should_stall: Value,
        flush_PC: Value,
        flush_offset: Value,
        branch_predict: Value,
        predict_offset: Value,
        decoder: Decoder,
        icache: SRAM,
    ):
        success_decode = should_stall.valid()
        should_stall = should_stall.optional(Bool(0))
        should_branch = branch_predict.optional(Bool(0))

        cancel_stall = flush_PC.valid() | flush_offset.valid()

        added_PC = flush_PC.optional(PC_addr) + flush_offset.optional(should_branch.select(predict_offset, Bits(32)(4)))

        new_stalled = (self.stalled[0] | should_stall) & ~cancel_stall

        new_PC = (cancel_stall | (~new_stalled & success_decode)).select(added_PC, PC_addr)

        icache.build(we=Bool(0), re=Bool(1), addr=new_PC[2:31].zext(Bits(32)), wdata=Bits(32)(0))
        PC_reg[0] = new_PC
        self.stalled[0] = new_stalled

        if self.verbose:
            log(
                "new_PC: 0x{:08X}, old_PC: 0x{:08X}, flush_PC: ({}, 0x{:08X}), flush_offset: ({}, 0x{:08X}), should_branch: {}, predict_offset: ({}, 0x{:08X}), success_decode: {}, new_stalled: {}",
                new_PC,
                PC_addr,
                flush_PC.valid(),
                flush_PC.optional(Bits(32)(0)),
                flush_offset.valid(),
                flush_offset.optional(Bits(32)(0)),
                should_branch,
                predict_offset.valid(),
                predict_offset.optional(Bits(32)(0)),
                success_decode,
                new_stalled,
            )

        with Condition(~new_stalled):
            decoder.bind(instruction_addr=new_PC)
