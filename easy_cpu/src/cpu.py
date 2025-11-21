from assassyn.frontend import *
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

    def __init__(self, sram_file: str | None):
        self.reg_file = RegFile()
        self.icache = SRAM(32, 32, sram_file)
        self.dcache = SRAM(32, 32, sram_file)

        self.fetcher = Fetcher()
        self.fetcher_impl = FetcherImpl()
        self.decoder = Decoder()
        self.executor = Executor()
        self.memory = Memory()
        self.write_back = WriteBack()

        self._connect()

    def _connect(self):
        instruction = self.icache.dout[0]

        PC = self.fetcher.build()
        success_decode, occupied_rd, should_stall = self.decoder.build(
            instruction, self.reg_file, self.reg_occupation, self.executor
        )
        self.executor.build(self.memory)
        self.memory.build(self.dcache, self.write_back)
        flush_PC, PC_adder, release_rd = self.write_back.build(self.reg_file, self.dcache)

        self.fetcher_impl.build(PC, success_decode, should_stall, flush_PC, PC_adder, self.decoder, self.icache)
        self.reg_occupation.build(occupied_rd, release_rd)
