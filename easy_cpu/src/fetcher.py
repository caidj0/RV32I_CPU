from assassyn.frontend import *
from decoder import Decoder
from utils import Bool


class Fetcher(Downstream):
    PC: Array

    def __init__(self):
        super().__init__()
        self.PC = RegArray(Bits(32), 1)

    # 设计接口时需要小心：如果它的上游均没有运行（即均触发了 wait_until），则下游根本不会运行
    @downstream.combinational
    def build(self, should_stall: Value, should_push: Value, flush_PC: Value, decoder: Decoder, icache: SRAM):

        new_PC = flush_PC.optional(should_stall.select(self.PC[0], self.PC[0] + Bits(32)(4)))
        icache.build(we=Bool(0), re=Bool(1), addr=new_PC, wdata=Bits(32)(0))
        self.PC[0] = new_PC

        with Condition(should_push):
            decoder.bind(instruction_addr=new_PC)
