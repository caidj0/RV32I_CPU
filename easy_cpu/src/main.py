import os
from assassyn.frontend import *
from assassyn.backend import elaborate
from assassyn.utils import run_simulator, run_verilator
from cpu import CPU


def main():
    sys = SysBuilder("easy_cpu")
    with sys:
        _ = CPU("asms/empty/empty.hex", verbose=True)
    sim, ver = elaborate(
        sys,
        verilog=True,
        verbose=False,
        sim_threshold=100,
        resource_base=os.getcwd(),
    )
    raw = run_simulator(sim)
    with open("out/empty.out", "w") as f:
        f.write(raw)


if __name__ == "__main__":
    main()
