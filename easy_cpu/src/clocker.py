from assassyn.frontend import *


class Driver(Module):
    def __init__(self):
        super().__init__(ports={})

    @module.combinational
    def build(self, modules: list[Module]):
        for module in modules:
            module.async_called()
