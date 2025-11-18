# pyright: reportAttributeAccessIssue = false

from enum import Enum
from assassyn.frontend import *
from assassyn.ir.expr import Bind


class RV32I_ALU(Enum):
    ADD = 0
    SUB = 1
    SLL = 2
    SLT = 3
    SLTU = 4
    XOR = 5
    SRA = 6
    SRL = 7
    OR = 8
    AND = 9


class ALU(Module):
    bus: Record

    def __init__(self):
        super().__init__(
            ports={
                "op": Port(Bits(len(RV32I_ALU))),
                "operant1": Port(Bits(32)),
                "operant2": Port(Bits(32)),
            }
        )

    @module.combinational
    def build(self, receiver: Port | tuple[Module | Bind, str]):
        pops: list[Value] = self.pop_all_ports(validate=True)
        op, operant1, operant2 = pops

        shifter = operant2[0:4]

        values = [Bits(32)(0)] * len(RV32I_ALU)
        values[RV32I_ALU.ADD.value] = operant1 + operant2
        values[RV32I_ALU.SUB.value] = operant1 - operant2
        values[RV32I_ALU.SLL.value] = operant1 << shifter
        values[RV32I_ALU.SLT.value] = (
            operant1.bitcast(Int(32)) < operant2.bitcast(Int(32))
        ).zext(Bits(32))
        values[RV32I_ALU.SLTU.value] = (operant1 < operant2).zext(Bits(32))
        values[RV32I_ALU.XOR.value] = operant1 ^ operant2
        values[RV32I_ALU.SRA.value] = (
            operant1.bitcast(Int(32)) >> operant2[0:4]
        ).bitcast(Bits(32))
        values[RV32I_ALU.SRL.value] = operant1 >> operant2[0:4]
        values[RV32I_ALU.OR.value] = operant1 | operant2
        values[RV32I_ALU.AND.value] = operant1 & operant2

        value = op.select1hot(*values)

        if isinstance(receiver, Port):
            receiver.push(value)
        else:
            module, name = receiver
            module.async_called(**{name: value})
