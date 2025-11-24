from assassyn.frontend import *
from utils import Bool


class Bypasser(Downstream):
    verbose: bool

    clocker: Array

    decoder_rd: Array
    alu_rd: Array
    mem_rd: Array

    def __init__(self, verbose: bool):
        super().__init__()
        self.clocker = RegArray(Bool, 1)
        self.decoder_rd = RegArray(Bits(5), 1)
        self.alu_rd = RegArray(Bits(5), 1)
        self.mem_rd = RegArray(Bits(5), 1)

        self.verbose = verbose

    @downstream.combinational
    def build(self, clocker: Value, decoder_rd: Value, alu_rd: Value, mem_rd: Value):
        self.clocker[0] = clocker[0:0]

        new_decoder_rd = decoder_rd.optional(Bits(5)(0))
        new_alu_rd = alu_rd.optional(Bits(5)(0))
        new_mem_rd = mem_rd.optional(Bits(5)(0))
        self.decoder_rd[0] = new_decoder_rd
        self.alu_rd[0] = new_alu_rd
        self.mem_rd[0] = new_mem_rd

        if self.verbose:
            log(
                "decoder_rd: {}, alu_rd: {}, mem_rd: {}",
                new_decoder_rd,
                new_alu_rd,
                new_mem_rd,
            )
