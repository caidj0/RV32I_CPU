from assassyn.frontend import *
from reg_file import RegFile, RegOccupation
from instruction import Instructions, default_instruction_arguments
from utils import Bool


class Decoder(Module):
    verbose: bool

    instruction_addr: Port

    def __init__(self, verbose: bool):
        super().__init__(ports={"instruction_addr": Port(Bits(32))})
        self.verbose = verbose

    @module.combinational
    def build(self, icache: SRAM, reg_file: RegFile, reg_occupation: RegOccupation, executor: Module):
        instruction_addr = self.pop_all_ports(validate=True)
        instruction = icache.dout[0]

        args = default_instruction_arguments()

        matched = Bool(0)

        for inst in Instructions:
            inst_cond = inst.value.matches(instruction)
            inst.value.select_args(inst_cond, instruction, args)
            matched |= inst_cond

        # assume(matched)

        # 常量不能检查 valid，因此需要一个 operator
        success_decode = Bool(0) | Bool(1)

        wait_until(
            ((~args.rs1.valid) | (reg_occupation[args.rs1.value] == Bits(2)(0)))
            & ((~args.rs2.valid) | (reg_occupation[args.rs2.value] == Bits(2)(0)))
        )

        with Condition(args.rs1.valid):
            executor.bind(rs1=reg_file.regs[args.rs1.value])

        with Condition(args.rs2.valid):
            executor.bind(rs2=reg_file.regs[args.rs2.value])

        args.bind_with(executor, ["rs1", "rs2", "just_stall"])
        executor.async_called(instruction_addr=instruction_addr)

        should_stall = args.is_branch.value | args.change_PC.value | args.just_stall.value

        if self.verbose:
            log(
                "Decode addr : 0x{:08X}, instruction: 0x{:08X}, imm: 0x{:08X}, should_stall: {}, rs1: ({}, {}, 0x{:08X}), rs2: ({}, {}, 0x{:08X})",
                instruction_addr,
                instruction,
                args.imm.value,
                should_stall,
                args.rs1.valid,
                args.rs1.value,
                reg_file.regs[args.rs1.value],
                args.rs2.valid,
                args.rs2.value,
                reg_file.regs[args.rs2.value],
            )

        return success_decode, args.rd.value, should_stall
