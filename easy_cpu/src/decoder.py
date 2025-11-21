from assassyn.frontend import *
from reg_file import RegFile, RegOccupation
from instruction import Instructions, default_instruction_arguments
from utils import Bool


class Decoder(Module):
    instruction_addr: Port

    def __init__(self):
        super().__init__(ports={"instruction_addr": Port(Bits(32))})

    @module.combinational
    def build(self, instruction: Value, reg_file: RegFile, reg_occupation: RegOccupation, executor: Module):
        instruction_addr = self.pop_all_ports(validate=True)

        args = default_instruction_arguments()

        for inst in Instructions:
            with Condition(inst.value.matches(instruction)):
                inst.value.set_args(instruction, args)

        # 常量不能检查 valid，因此需要一个 operator
        success_decode = Bool(0)

        with Condition(args.rs1.valid):
            wait_until(reg_occupation[args.rs1.value] == Bits(2)(0))
            executor.bind(rs1=reg_file.regs[args.rs1.value])

        with Condition(args.rs2.valid):
            wait_until(reg_occupation[args.rs2.value] == Bits(2)(0))
            executor.bind(rs2=reg_file.regs[args.rs2.value])

        args.bind_with(executor, ["rs1", "rs2"])
        executor.async_called(instruction_addr=instruction_addr)

        success_decode |= Bool(1)

        should_stall = args.is_branch.value | args.change_PC.value | args.just_stall
        return success_decode, args.rd.value, should_stall
