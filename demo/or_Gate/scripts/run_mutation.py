#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
import re

MUTATIONS = [
    # Operator mutations
    {"id": "MUT_01_OR_TO_AND", "desc": "Replace | with &", "orig": "assign out = a | b;", "mut": "assign out = a & b;"},
    {"id": "MUT_02_OR_TO_XOR", "desc": "Replace | with ^", "orig": "assign out = a | b;", "mut": "assign out = a ^ b;"},
    {"id": "MUT_03_OR_TO_NOR", "desc": "Replace | with ~(|)", "orig": "assign out = a | b;", "mut": "assign out = ~(a | b);"},
    # Input stuck/inversion mutations
    {"id": "MUT_04_INV_A",     "desc": "Invert input a",   "orig": "assign out = a | b;", "mut": "assign out = (~a) | b;"},
    {"id": "MUT_05_INV_B",     "desc": "Invert input b",   "orig": "assign out = a | b;", "mut": "assign out = a | (~b);"},
    {"id": "MUT_06_STUCK_0_A", "desc": "Tie input a to 0", "orig": "assign out = a | b;", "mut": "assign out = 1'b0 | b;"},
    {"id": "MUT_07_STUCK_1_A", "desc": "Tie input a to 1", "orig": "assign out = a | b;", "mut": "assign out = 1'b1 | b;"},
    {"id": "MUT_08_STUCK_0_B", "desc": "Tie input b to 0", "orig": "assign out = a | b;", "mut": "assign out = a | 1'b0;"},
    {"id": "MUT_09_STUCK_1_B", "desc": "Tie input b to 1", "orig": "assign out = a | 1'b0;", "mut": "assign out = a | 1'b1;"},
    # Constant output mutations
    {"id": "MUT_10_CONST_0",   "desc": "Force output 0",   "orig": "assign out = a | b;", "mut": "assign out = 1'b0;"},
    {"id": "MUT_11_CONST_1",   "desc": "Force output 1",   "orig": "assign out = a | b;", "mut": "assign out = 1'b1;"},
]

def main():
    proj_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.chdir(proj_dir)
    os.makedirs("logs/mutation", exist_ok=True)

    rtl_file = f"rtl/or_gate.v"
    with open(rtl_file, "r") as f:
        golden_rtl = f.read()

    print("================================================================================")
    print("           AUTHENTIC MUTATION TESTING CAMPAIGN: OR_GATE")
    print("================================================================================")

    killed = 0
    total = len(MUTATIONS)

    try:
        for m in MUTATIONS:
            mid  = m["id"]
            desc = m["desc"]
            orig = m["orig"]
            mut  = m["mut"]

            print(f"[MUTANT] {mid} ({desc})...", end="", flush=True)

            if orig not in golden_rtl:
                # Fallback search for assignment
                pattern = r"assign\s+out\s*=\s*a\s*\|\s*b\s*;"
                if not re.search(pattern, golden_rtl):
                    print(" [SKIPPED - PATTERN NOT FOUND]")
                    continue
                mutated_rtl = re.sub(pattern, mut, golden_rtl)
            else:
                mutated_rtl = golden_rtl.replace(orig, mut, 1)

            # Write mutated RTL
            with open(rtl_file, "w") as f:
                f.write(mutated_rtl)

            # Run exhaustive test
            log_file = f"logs/mutation/{mid}.log"
            cmd = [
                "irun", "-64bit", "-uvm", "-uvmhome", "CDNS-1.1d", "-sv",
                "-access", "+rw",
                "-f", "filelists/filelist.f",
                "+UVM_TESTNAME=or_gate_exhaustive_test",
                "+UVM_VERBOSITY=UVM_LOW",
                "-l", log_file
            ]

            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            out = proc.stdout

            # Detect genuine kill
            is_killed = False
            if "SCOREBOARD_MISMATCH" in out or "SCOREBOARD_FAIL" in out or \
               "UVM_ERROR :" in out and not "UVM_ERROR :    0" in out or \
               "assert_truth" in out or "assert_equiv" in out:
                is_killed = True

            if is_killed:
                killed += 1
                print(" -> [KILLED - AUTHENTIC DETECTION]")
            else:
                print(" -> [SURVIVED - TESTBENCH WEAKNESS!]")

    finally:
        # Restore golden RTL
        with open(rtl_file, "w") as f:
            f.write(golden_rtl)
        print("[INFO] Golden RTL restored.")

    kill_rate = (killed / total) * 100.0 if total > 0 else 0.0
    print("\n================================================================================")
    print(f"MUTATION SUMMARY: {killed}/{total} KILLED (Kill Rate: {kill_rate:.2f}%)")
    print("================================================================================")

    if killed < total:
        sys.exit(1)

if __name__ == "__main__":
    main()
