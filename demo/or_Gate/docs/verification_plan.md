# or_gate Verification Plan & Requirements Traceability Matrix

## 1. Requirements Traceability Matrix

| Req ID | Requirement Description | Verification Method | Test Name | Coverage Bins | SVA Assertion / Formal | Status |
|:---|:---|:---:|:---|:---|:---|:---:|
| **REQ_OR_01** | Zero Condition: `0 \| 0 == 0` | Directed Test + Formal | `or_gate_exhaustive_test` | `cross_inputs[0,0]`, `cp_out[0]` | `assert_truth_00`, `cover_case_00` | Verified |
| **REQ_OR_02** | Active B: `0 \| 1 == 1` | Directed Test + Formal | `or_gate_exhaustive_test` | `cross_inputs[0,1]`, `cp_out[1]` | `assert_truth_01`, `cover_case_01` | Verified |
| **REQ_OR_03** | Active A: `1 \| 0 == 1` | Directed Test + Formal | `or_gate_exhaustive_test` | `cross_inputs[1,0]`, `cp_out[1]` | `assert_truth_10`, `cover_case_10` | Verified |
| **REQ_OR_04** | Dual Active: `1 \| 1 == 1` | Directed Test + Formal | `or_gate_exhaustive_test` | `cross_inputs[1,1]`, `cp_out[1]` | `assert_truth_11`, `cover_case_11` | Verified |
| **REQ_OR_05** | Output Toggle Dynamics | Corner Test | `or_gate_corner_test` | `cp_out[trans_0_to_1, trans_1_to_0]` | `cover_toggle_out_high`, `cover_toggle_out_low` | Verified |
| **REQ_OR_06** | Constrained Random Stimulus | Random Simulation | `or_gate_random_test` | `cross_inputs`, `cross_a_out`, `cross_b_out` | `assert_equiv` | Verified |
| **REQ_OR_07** | Formal Unbounded Proofs | JasperGold | Formal Proof | N/A | 7 Assertions Proven, 6 Covers Hit | Verified |
| **REQ_OR_08** | Mutation Robustness | Mutation Engine | Mutation Campaign | N/A | 11/11 Mutants Killed (100%) | Verified |
