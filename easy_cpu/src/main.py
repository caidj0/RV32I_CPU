from assassyn.frontend import *
from assassyn.backend import elaborate
from assassyn.utils import run_simulator, run_verilator
from cpu import CPU


def main():
    sys = SysBuilder("easy_cpu")
    with sys:
        _ = CPU("asms/empty.hex")
    sim, ver = elaborate(sys, verilog=True, resource_base=".")
    raw = run_simulator(sim)
    print(raw)


if __name__ == "__main__":
    main()
