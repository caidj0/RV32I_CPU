from assassyn.frontend import *
from bypass import Bypasser
from clocker import Driver
from decoder import Decoder
from executor import Executor
from memory import Memory
from reg_file import RegFile, RegOccupation
from fetcher import Fetcher, FetcherImpl
from utils import Bool
from write_back import WriteBack


class CPU:
    reg_file: RegFile
    reg_occupation: RegOccupation

    icache: SRAM
    dcache: SRAM

    fetcher: Fetcher
    fetcher_impl: FetcherImpl
    decoder: Decoder
    executor: Executor
    memory: Memory
    write_back: WriteBack
    bypasser: Bypasser

    clocker: Driver

    def __init__(self, sram_file: str | None, verbose: bool = False):
        self.reg_file = RegFile()
        self.icache = SRAM(32, 0x100000, sram_file)
        self.dcache = SRAM(32, 0x100000, sram_file)

        self.fetcher = Fetcher()
        self.fetcher_impl = FetcherImpl(verbose)
        self.decoder = Decoder(verbose)
        self.executor = Executor(verbose)
        self.memory = Memory(verbose, self.dcache)
        self.write_back = WriteBack(verbose)
        self.reg_occupation = RegOccupation()
        self.bypasser = Bypasser(verbose)

        self.clocker = Driver()

        self._build()

    def _build(self):
        self.clocker.build([self.fetcher, self.decoder])

        PC_reg, PC_addr = self.fetcher.build()
        should_stall, decoder_rd = self.decoder.build(
            self.icache, self.reg_file, self.reg_occupation, self.executor, self.memory, self.bypasser
        )
        alu_rd = self.executor.build(self.memory)
        mem_rd = self.memory.build(self.write_back)
        flush_PC, branch_offset, release_rd = self.write_back.build(self.reg_file, self.memory)

        self.fetcher_impl.build(PC_reg, PC_addr, should_stall, flush_PC, branch_offset, self.decoder, self.icache)
        self.reg_occupation.build(decoder_rd, release_rd)
        self.bypasser.build(PC_addr, decoder_rd, alu_rd, mem_rd)
