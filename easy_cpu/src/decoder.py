from assassyn.frontend import *
from bypass import Bypasser
from executor import Executor
from memory import Memory
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
    def build(
        self,
        icache: SRAM,
        reg_file: RegFile,
        reg_occupation: RegOccupation,
        executor: Executor,
        memory: Memory,
        bypasser: Bypasser,
    ):
        instruction_addr: Value = self.pop_all_ports(validate=True)  # pyright: ignore[reportAssignmentType]
        instruction = icache.dout[0]

        args = default_instruction_arguments()

        matched = Bool(0)

        for inst in Instructions:
            inst_cond = inst.value.matches(instruction)
            inst.value.select_args(inst_cond, instruction, args)
            matched |= inst_cond

        assume(matched)

        def is_rs_valid(rs: Value):
            return (reg_occupation[rs] == UInt(2)(0)) | (
                (rs != bypasser.decoder_rd[0]) & ((rs == bypasser.alu_rd[0]) | (rs == bypasser.mem_rd[0]))
            )

        is_rs1_valid = is_rs_valid(args.rs1.value)
        is_rs2_valid = is_rs_valid(args.rs2.value)
        wait_until(is_rs1_valid & is_rs2_valid)

        def rs_selector(rs: Value):
            is_x0 = rs == Bits(5)(0)
            from_reg = reg_occupation[rs] == UInt(2)(0)
            from_alu = rs == bypasser.alu_rd[0]
            from_mem = rs == bypasser.mem_rd[0]

            assume(is_x0 | (from_reg ^ (from_alu | from_mem)))

            val = from_reg.select(reg_file.regs[rs], from_alu.select(executor.get_out(), memory.get_out()))
            return is_x0.select(reg_file.regs[0], val)

        rs1_data = rs_selector(args.rs1.value)
        rs2_data = rs_selector(args.rs2.value)
        with Condition(args.rs1.valid):
            executor.bind(rs1=rs1_data)

        with Condition(args.rs2.valid):
            executor.bind(rs2=rs2_data)

        args.bind_with(executor, ["rs1", "rs2", "just_stall"])
        executor.async_called(instruction_addr=instruction_addr)

        should_stall = args.change_PC.value | args.just_stall.value

        with Condition(args.is_branch.value):
            branch_addr = instruction_addr & instruction_addr
            predict_offset = args.imm.value & args.imm.value

        if self.verbose:
            log(
                "Decode addr : 0x{:08X}, instruction: 0x{:08X}, imm: 0x{:08X}, should_stall: {}, rs1: ({}, {}, 0x{:08X}), rs2: ({}, {}, 0x{:08X})",
                instruction_addr,
                instruction,
                args.imm.value,
                should_stall,
                args.rs1.valid,
                args.rs1.value,
                rs1_data,
                args.rs2.valid,
                args.rs2.value,
                rs2_data,
            )

        return should_stall, args.rd.value, branch_addr, predict_offset
