from assassyn.frontend import *
from reg_file import RegFile, RegOccupation
from instruction import Instructions, InstructionArgs, default_instruction_arguments
from alu import RV32I_ALU, BitsALU
from utils import Bool


class Decoder(Module):
    instruction_addr: Port

    def __init__(self):
        super().__init__(
            ports={
                "instruction_addr": Port(Bits(32))
            }
        )

    @module.combinational
    def build(self, instruction: Value, reg_file: RegFile, reg_occupation: RegOccupation):
        instruction_addr = self.pop_all_ports(validate=True)

        args = default_instruction_arguments()

        for inst in Instructions:
            with Condition(inst.value.matches(instruction)):
                inst.value.set_args(instruction, args)

        # 常量不能检查 valid，因此需要一个 operator
        success_decode = (Bool(1) | Bool(1)) 

        with Condition(args.rs1_valid):
            wait_until(reg_occupation[args.rs1] == Bits(2)(0))

        with Condition(args.rs2_valid):
            wait_until(reg_occupation[args.rs2] == Bits(2)(0))

        # TODO: bind 到 executor

        return success_decode

        


            