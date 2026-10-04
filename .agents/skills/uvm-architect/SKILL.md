---
name: uvm-architect
description: Comprehensive methodology, templates, and execution guide for architecting, synthesizing, running, and signing off industry-grade UVM verification environments from scratch or user specifications for any arbitrary digital design. Covers pure RTL, non-intrusive SVA bind, modular TB hierarchy, independent reference modeling, lockstep scoreboards, dual-domain coverage closure, Cadence Xcelium/Incisive simulation, JasperGold formal proofs, IMC coverage merging, authentic mutation testing, known gotchas/pitfalls mitigation, and complete verification signoff documentation.
---

# UVM Verification Architect: Production Environment Guide

This skill defines the complete, production-grade methodology for architecting, generating, executing, and signing off Universal Verification Methodology (UVM) environments from scratch for any digital design—ranging from basic logic blocks (e.g., gates, arbiters, multiplexers) to complex processors, pipelines, and protocol interfaces.

Every verification environment constructed under this skill adheres to zero-compromise industry standards established across real-world chip tapeouts.

---

## 1. Golden Verification Tenets

### Tenet 1: Pure Synthesizable RTL Separation
- The RTL module (`rtl/<design>.v` or `rtl/<design>.sv`) MUST contain **only synthesizable RTL code**.
- NEVER embed verification code, assertions, testbench hooks, or simulation-only tasks inside the RTL files.
- The RTL must remain identical to what is fed into synthesis and physical design tools.

### Tenet 2: External SVA Assertion Module & Non-Intrusive `bind`
- All SystemVerilog Assertions (SVA), concurrent properties, sequence declarations, and cover properties MUST reside in a dedicated assertion module (`assertions/<design>_assertions.sv`).
- Bind the assertion module non-intrusively to the DUT using the SystemVerilog `bind` directive:
  ```systemverilog
  bind <design_module_name> <design_module_name_assertions> u_<design_module_name_assertions> (.*);
  ```
- Port dimensioning, vector bit order (`[N-1:0]` vs `[0:N-1]`), and signal types in the assertion module must match the RTL interface exactly.

### Tenet 3: Modular Industry Directory Layout
Every project created must follow this standard directory structure:
```text
<design_root>/
├── rtl/                        # Pure synthesizable RTL modules
│   └── <design>.v
├── assertions/                 # Formal & simulation SVA assertions
│   └── <design>_assertions.sv
├── tb/                         # Complete UVM TB component hierarchy
│   ├── <design>_if.sv
│   ├── <design>_seq_item.sv
│   ├── <design>_sequencer.sv
│   ├── <design>_driver.sv
│   ├── <design>_monitor.sv
│   ├── <design>_ref_model.sv
│   ├── <design>_scoreboard.sv
│   ├── <design>_coverage.sv
│   ├── <design>_agent.sv
│   ├── <design>_env_cfg.sv
│   ├── <design>_env.sv
│   ├── <design>_virtual_sequencer.sv
│   ├── <design>_virtual_sequence.sv
│   ├── <design>_tb_pkg.sv
│   └── top.sv
├── tests/                      # Sequences and test classes
│   ├── <design>_sequence.sv
│   └── <design>_test.sv
├── formal/                     # Cadence JasperGold formal proof scripts
│   ├── run.jg
│   └── jaspergold_formal.log
├── filelists/                  # Tool filelists
│   ├── filelist.f              # Incisive/Xcelium simulation with assertions bound
│   └── formal.f                # JasperGold formal proof compilation
├── scripts/                    # Regression & mutation automation
│   ├── run_regression.sh       # tcsh Cadence environment wrapper
│   ├── run_regression.py       # Python runner with 12-column CSV report
│   └── run_mutation.py         # Authentic mutation testing engine
├── verification/               # Cumulative coverage outputs
│   └── coverage/final/
│       ├── final_summary.rpt
│       ├── final_functional.rpt
│       └── final_code.rpt
└── docs/                       # Verification signoff documentation suite
    ├── <design>_spec.md        # Architectural & functional specification
    ├── verification_plan.md    # Requirements traceability matrix (vPlan)
    ├── coverage_waivers.md     # Documented and justified coverage waivers
    └── signoff_report.md       # Final signoff evidence & verdict
```

### Tenet 4: Cycle-Accurate Interface & Timing Control
- The SystemVerilog interface (`tb/<design>_if.sv`) defines physical ports, clocking blocks, and modports.
- For combinational designs, the interface provides a testbench clock and synchronous strobes to eliminate simulator delta-cycle race conditions.
- Driver drives stimulus synchronously on `@(posedge vif.clk)` or clocking block edges (`drv_cb`).
- Monitor samples DUT responses synchronously or after non-blocking assignment delta delays (`#1step` or `@(negedge vif.clk)`).
- All interface inputs must be initialized to 2-state defaults (e.g. `logic a = 1'b0;`) to avoid time-0 unknown states.

### Tenet 5: Pure Observer Monitor with TLM Analysis Ports
- The monitor (`tb/<design>_monitor.sv`) is strictly passive; it NEVER alters DUT state or drives signals.
- Broadcasts observed transactions through `uvm_analysis_port #(<design>_seq_item) ap;`.
- Captures primary inputs and observed DUT outputs simultaneously to preserve transaction identity.

### Tenet 6: Independent Cycle-Accurate Reference Model
- The reference model (`tb/<design>_ref_model.sv`) predicts expected DUT behavior independently.
- It must NEVER sample internal RTL wires or cheat by reading the DUT's private registers.
- Given input stimulus $X$, compute expected output $Y_{\text{expected}} = f(X)$.

### Tenet 7: Lockstep Retirement & Per-Op Scoreboard
- The scoreboard (`tb/<design>_scoreboard.sv`) checks **every single transaction / operation** in lockstep, not merely end-of-test state.
- Compares expected vs actual results with strict equality (`===` / `!==`).
- Maintains:
  - `vector_count`: Total transactions checked
  - `pass_count`: Total matched operations
  - `error_count`: Total mismatches detected
- On any mismatch: produces an immediate `UVM_ERROR` displaying stimulus, expected result, and actual result.
- In `report_phase()`: reports total vectors, passes, and fails. Emits `UVM_FATAL` if `error_count > 0` or if no vectors ran.

### Tenet 8: Functional Coverage Closure & Dual-Domain Sampling
- The coverage subscriber (`tb/<design>_coverage.sv`) measures verification completeness.
- Includes coverpoints for:
  - Valid stimulus combinations (truth table, opcodes, operand boundaries).
  - Transition coverage (`0 => 1`, `1 => 0`, state sequences).
  - Cross coverage between critical input dimensions.
  - Dedicated value coverpoints (`cp_a_val`, `cp_out_val`) for input-output crosses.
- Declare explicit `ignore_bins` for functionally unreachable combinations (e.g., in an OR gate, `a=1` while `out=0`).

### Tenet 9: Formal Property Verification (JasperGold)
- Cadence JasperGold proof script (`formal/run.jg`) compiles RTL and SVA assertions.
- Prove 100% of safety assertions (`assert property`) as **proven** (unbounded proof at Infinite depth).
- Check **vacuity**: Every assertion must have a corresponding `cover property` to prove that the antecedent is reachable.

### Tenet 10: Automated Regression & 12-Column CSV Report
- Regressions are orchestrated via `scripts/run_regression.sh` and `scripts/run_regression.py`.
- Outputs an industry-standard 12-column CSV report:
  `Test_Name, Seed, Status, Errors, Warnings, Simulation_Time_ns, CPU_Time_s, Functional_Cov_Pct, Code_Cov_Pct, Log_Path, Artifact_Dir, Signature`
- Merges all individual test coverage runs using Cadence IMC into a unified cumulative database (`cov_work/scope/final_merged`).

### Tenet 11: Authentic Mutation Testing
- Synthesizes systematic single-point syntactic mutations across RTL operators, conditions, and constants.
- Detects genuine failures (`UVM_ERROR`, `UVM_FATAL`, SVA assertion failures).
- Avoids false kills: does not treat normal watchdog messages or harmless warnings as mutant kills.
- Requires 100% kill rate across all non-equivalent synthetic mutants.

### Tenet 12: Production Signoff Documentation
- `docs/<design>_spec.md`: Microarchitecture specification and timing diagrams.
- `docs/verification_plan.md`: Traceability matrix mapping requirements (`REQ_*`) to tests (`TEST_*`), coverage (`COV_*`), and assertions (`SVA_*`).
- `docs/coverage_waivers.md`: Formal waiver rationale, impact analysis, and signed approval.
- `docs/signoff_report.md`: Final verdict, comprehensive metrics table, tool versions, and signoff approval.

---

## 2. Verification Gotchas, Pitfalls, & Mitigation Strategies

During real-world verification synthesis and signoff on Cadence toolchains, the following pitfalls must be avoided:

### Gotcha 1: JasperGold Combinational Formal Switches
- **Pitfall**: Specifying `clock -implicit` causes `ERROR (ESW087): No such switch "-implicit"`. Omitting reset definitions causes `ERROR (ERS033): Reset information is not defined`. Calling `cover -all` after `prove -all` triggers `ERROR (ESW087): No such switch "-all"`.
- **Mitigation**: For combinational designs without explicit clock or reset pins, configure JasperGold with:
  ```tcl
  clock -none
  reset -none
  prove -all
  report -summary
  report -results
  ```
  `prove -all` automatically proves both assertions and covers.

### Gotcha 2: Time-0 False Assertion Failures on Uninitialized 4-State Signals
- **Pitfall**: At simulation start (`time 0 FS`), interface nets may float at `1'bx` before initial blocks or driver resets evaluate, triggering immediate assertion failures (`*E,ASRTST`).
- **Mitigation**: Guard every SVA assertion and cover property with:
  ```systemverilog
  disable iff ($time == 0 || $isunknown({a, b, out}))
  ```
  Additionally, initialize interface logic variables directly at declaration (e.g. `logic a = 1'b0; logic b = 1'b0;`).

### Gotcha 3: Multiple Timescale Conflict
- **Pitfall**: Specifying `-timescale 1ns/1ps` in both `filelists/filelist.f` and on the simulation command line causes:
  `irun: *E,OPTNOML: Multiple -timescale option specified, only 1 required`.
- **Mitigation**: Define `-timescale 1ns/1ps` exclusively in `filelists/filelist.f` and omit it from shell command invocations.

### Gotcha 4: Toolchain Version Mismatch (Incisive vs Xcelium vs IMC)
- **Pitfall**: If the environment's `PATH` resolves `imc` to an older release (e.g. `/cadence/INCISIVE152/bin/imc`) while simulations run with newer `xrun` (Xcelium 20.03), IMC will fail to parse the database with:
  `*W,SMER04: Reading of ucm file failed... Target model generation failed`.
- **Mitigation**: Always match the simulator and coverage analyzer:
  * For Incisive environments: Run `irun -64bit -uvm -uvmhome CDNS-1.1d ...` with `imc`.
  * For Xcelium environments: Prepend `/cadence/VMANAGER2003/bin` to `PATH` before invoking `imc`.

### Gotcha 5: Mutually Exclusive IMC Command-Line Flags
- **Pitfall**: Running `imc -batch -licqueue -exec <script>` crashes with:
  `imc: *E,CMDERR: Command line error: an option from this group has already been selected: 'batch'`.
- **Mitigation**: In IMC, `-exec <script>` already executes non-interactively in batch mode. Use:
  ```bash
  imc -licqueue -exec merge_coverage.tcl
  ```

### Gotcha 6: Coverage Directory Scoping for Automatic Merge
- **Pitfall**: Using `-covscope <tag>` places tests under non-standard hierarchies, breaking IMC's wildcard discovery (`cov_work/scope/*`).
- **Mitigation**: Standardize simulation coverage flags on:
  ```bash
  -coverage all -covoverwrite -covworkdir cov_work -covtest <test_run_tag>
  ```
  This creates the model file in `cov_work/scope/` and data in `cov_work/scope/<tag>/`, allowing clean wildcard merging in TCL:
  ```tcl
  merge * -initial_model union_all -out final_merged -overwrite
  load cov_work/scope/final_merged
  ```

### Gotcha 7: Unreachable Transition Cross Coverage Bins
- **Pitfall**: Crossing coverpoints that contain transition bins (e.g. `0 => 1`) directly with other signals or output transitions creates combinations that are physically impossible in Boolean logic (e.g. an OR gate where `a=1` while `out` transitions `1->0`). These unreachable bins drag down cumulative coverage and prevent 100% closure.
- **Mitigation**: Separate transition dynamics from functional value mapping. Create dedicated value coverpoints (`cp_a_val`, `cp_out_val`) for input-output crosses, and explicitly declare `ignore_bins` for functionally impossible combinations:
  ```systemverilog
  cross_a_out: cross cp_a_val, cp_out_val {
      ignore_bins unreach_a1_out0 = binsof(cp_a_val.one) && binsof(cp_out_val.zero);
  }
  ```

### Gotcha 8: Windows/Linux Line Endings & TCSH Redirects
- **Pitfall**: Files edited on Windows have CRLF line endings (`\r\n`), causing Linux `tcsh` or `bash` to crash with `Command not found`. Furthermore, `tcsh` rejects `> file 2>&1` with `Ambiguous output redirect`.
- **Mitigation**: Strip carriage returns (`sed -i 's/\r$//'`) and use `tcsh` compatible redirects (`>& logfile`).

---

## 3. Remote Tool Invocations on EDA Server

On the EDA server (`edatools-server1.iiitd.edu.in`), tools must be invoked through `tcsh` after sourcing the Cadence environment setup:

```bash
tcsh -c "source /cadence/cshrc; <command>"
```

### Simulation Command (Incisive / Xcelium)
```bash
irun -64bit -uvm -uvmhome CDNS-1.1d -sv \
     -access +rw \
     -f filelists/filelist.f \
     +UVM_TESTNAME=<test_name> \
     +UVM_VERBOSITY=UVM_LOW \
     -svseed <seed> \
     -coverage all \
     -covoverwrite \
     -covworkdir cov_work \
     -covtest <test_tag> \
     -l logs/<test_tag>.log
```

### JasperGold Formal Verification Command
```bash
jg -batch -tcl formal/run.jg >& formal/jaspergold_formal.log
```

### Cadence IMC Coverage Merge & Report Command
```bash
imc -licqueue -exec merge_coverage.tcl
```
Where `merge_coverage.tcl` contains:
```tcl
merge * -initial_model union_all -out final_merged -overwrite
load cov_work/scope/final_merged
report -summary -out verification/coverage/final/final_summary.rpt
report -detail -metrics functional -both -out verification/coverage/final/final_functional.rpt
report -detail -metrics code -both -out verification/coverage/final/final_code.rpt
exit
```
