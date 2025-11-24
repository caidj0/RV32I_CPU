import os
from assassyn.frontend import *
from assassyn.backend import elaborate
from assassyn.utils import run_simulator, run_verilator
from cpu import CPU


def main():
    sys = SysBuilder("easy_cpu")
    with sys:
        _ = CPU("asms/primes/primes.hex", verbose=False)
    sim, ver = elaborate(
        sys,
        verilog=True,
        verbose=False,
        sim_threshold=100000,
        resource_base=os.getcwd(),
    )
    raw = run_simulator(sim)
    with open("out/primes.out", "w") as f:
        f.write(raw)


if __name__ == "__main__":
    main()
