from assassyn.frontend import *
from assassyn.backend import elaborate
from assassyn.utils import run_simulator, run_verilator
from cpu import CPU


def main():
    sys = SysBuilder("easy_cpu")
    with sys:
        _ = CPU("asms/sum.hex", verbose=False)
    sim, ver = elaborate(sys, verilog=True, verbose=False, resource_base="/workspaces/assassyn_ws/RV32I_CPU/easy_cpu")
    raw = run_simulator(sim)
    with open("out/sum.out", "w") as f:
        f.write(raw)


if __name__ == "__main__":
    main()
