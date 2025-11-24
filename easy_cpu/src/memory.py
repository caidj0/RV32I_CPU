from assassyn.frontend import *
from instruction import MO_LEN, MemoryOperation
from utils import Bool, forward_ports, peek_or, pop_or


class Memory(Module):
    verbose: bool

    instruction_addr: Port
    rd: Port
    rs1: Port
    rs2: Port
    imm: Port
    memory_operation: Port
    is_branch: Port
    branch_flip: Port
    change_PC: Port
    alu_result: Port
    is_jalr: Port

    alu_out: Array
    is_memory_out: Array
    dcache: SRAM

    def __init__(self, verbose: bool, dcache: SRAM):
        super().__init__(
            ports={
                "instruction_addr": Port(Bits(32)),
                "rd": Port(Bits(5)),
                "rs1": Port(Bits(32)),
                "rs2": Port(Bits(32)),
                "imm": Port(Bits(32)),
                "memory_operation": Port(Bits(MO_LEN)),
                "is_branch": Port(Bool),
                "branch_flip": Port(Bool),
                "change_PC": Port(Bool),
                "alu_result": Port(Bits(32)),
                "is_jalr": Port(Bool),
            }
        )
        self.verbose = verbose
        self.alu_out = RegArray(Bits(32), 1)
        self.is_memory_out = RegArray(Bool, 1)
        self.dcache = dcache

    @module.combinational
    def build(self, write_back: Module):
        need_mem = self.memory_operation.valid()

        memory_operation = pop_or(self.memory_operation, Bits(MO_LEN)(0))
        alu_result = self.alu_result.pop()
        addr = need_mem.select(alu_result, Bits(32)(0))
        peek_or(self.rs1, Bits(32)(0))
        raw_wdata = pop_or(self.rs2, Bits(32)(0))

        raw_re = memory_operation <= Bits(MO_LEN)(MemoryOperation.LOAD_HALFU.value)
        re = need_mem & raw_re
        we = need_mem & (~raw_re)

        wdata = memory_operation.case(
            {
                None: raw_wdata,  # pyright: ignore[reportArgumentType]
                Bits(MO_LEN)(MemoryOperation.STORE_BYTE.value): raw_wdata & Bits(32)(0xFF),
                Bits(MO_LEN)(MemoryOperation.STORE_HALF.value): raw_wdata & Bits(32)(0xFFFF),
            }
        )

        # 注意 sram 一个地址对应一个字，从而地址需要截断
        self.dcache.build(we, re, addr[2:31].zext(Bits(32)), wdata)

        self.is_memory_out[0] = need_mem
        self.alu_out[0] = alu_result

        if self.verbose:
            log("we: {}, re: {}, addr: 0x{:08X}, wdata: 0x{:08X}", we, re, addr, wdata)

        rd = peek_or(self.rd, Bits(5)(0))

        forward_ports(
            write_back,
            [
                self.instruction_addr,
                self.rd,
                self.rs1,
                self.imm,
                self.is_branch,
                self.branch_flip,
                self.change_PC,
                self.is_jalr,
            ],
        )

        write_back.async_called()

        return rd

    def get_out(self) -> Value:
        # TODO: 添加字节、半字支持
        return self.is_memory_out[0].select(self.dcache.dout[0], self.alu_out[0])
