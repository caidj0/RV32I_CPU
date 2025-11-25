import os
import re
import shutil

from assassyn.frontend import *
from assassyn.backend import elaborate
from assassyn.utils import run_simulator

from cpu import CPU
from predictor import BinaryPredictState, BinaryPredictor
from utils import run_quietly

test_cases_path = "asms"
work_path = "tmp"


def get_predictor():
    return BinaryPredictor(5, BinaryPredictState.WeaklyB)


def test_asms():
    work_hex_path = os.path.join(work_path, "exe.hex")

    os.makedirs(work_path, exist_ok=True)
    sys = SysBuilder("easy_cpu")
    with sys:
        _ = CPU(work_hex_path, get_predictor, verbose=False)
    sim, _ = elaborate(sys, verbose=False, sim_threshold=1000000, resource_base=os.getcwd())

    test_cases = os.listdir(test_cases_path)
    print(test_cases)

    for test_case in test_cases:
        hex_path = os.path.join(test_cases_path, test_case, test_case + ".hex")
        out_path = os.path.join(test_cases_path, test_case, test_case + ".out")
        with open(out_path, "r") as f:
            expected_result = int(f.readline())

        shutil.copyfile(hex_path, work_hex_path)

        raw, _, stderr = run_quietly(run_simulator, sim)
        assert isinstance(raw, str), f"Run simulator failed with stderr: \n {stderr}"

        result = raw.splitlines()[-1]
        assert (
            "WriteBackInstance" in result and "instruction_addr=0x00000008" in result
        ), f"The processor is not down properly while testing {test_case}"

        ret = re.search(r"x10=(0x[0-9a-fA-F]+)", result)
        assert ret, f"Can't find result in the last line of output while testing {test_case}"
        ret = int(ret.group(1), 16)
        assert ret == expected_result, f"Test failed for {test_case}: expect result is {expected_result}, get {ret}"
        print(f"{test_case} passed!")
