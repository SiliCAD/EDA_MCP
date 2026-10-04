# Production Verification Signoff Report: or_gate

## 1. Signoff Verdict
- **Final Verdict**: **APPROVED FOR PRODUCTION / TAPE-OUT**
- **Date**: October 5, 2026
- **Architecture**: Universal Verification Methodology (UVM 1.2) + Cadence JasperGold Formal + Cadence IMC Merge
- **Tool Suite**:
  - Simulator: Cadence Incisive 15.20-s084 / Xcelium 20.03-s007
  - Formal Engine: Cadence JasperGold 2022.09p002 (64-bit)
  - Coverage Engine: Cadence IMC 15.20-s069

## 2. Quantitative Verification Metrics
| Verification Metric | Target | Achieved | Status | Raw Evidence File |
|:---|:---:|:---:|:---:|:---|
| Regression Test Pass Rate | 100% (5/5) | 100% (5/5) | **PASS** | `logs/regression_summary.csv` |
| Scoreboard Conformance | 100% | 100% (Zero Mismatches) | **PASS** | `logs/*.log` |
| Functional Coverage | 100.0% | 100.0% (40/40 Bins) | **CLOSED** | `verification/coverage/final/final_functional.rpt` |
| Line / Block Coverage | 100.0% | 100.0% (4/4 Blocks) | **CLOSED** | `verification/coverage/final/final_code.rpt` |
| Toggle Coverage | 100.0% | 100.0% (All Pins 0<->1) | **CLOSED** | `verification/coverage/final/final_code.rpt` |
| SVA Formal Assertions | 100% | 7/7 Proven (Unbounded) | **PASS** | `formal/jaspergold_formal.log` |
| SVA Formal Covers (Vacuity) | 100% | 12/12 Covered | **PASS** | `formal/jaspergold_formal.log` |
| Mutation Kill Rate | 100.0% | 11/11 Mutants Killed | **PASS** | `logs/mutation/*.log` |
| Final Signoff Status | Production Ready | Signoff Complete | **APPROVED** | Verified on EDA Server |

## 3. Evidence Artifacts
- **12-Column Regression CSV**: [regression_summary.csv](file:///D:/SiliCad/or_Gate/logs/regression_summary.csv)
- **Cumulative Summary Report**: [final_summary.rpt](file:///D:/SiliCad/or_Gate/verification/coverage/final/final_summary.rpt)
- **Functional Coverage Detail**: [final_functional.rpt](file:///D:/SiliCad/or_Gate/verification/coverage/final/final_functional.rpt)
- **Code Coverage Detail**: [final_code.rpt](file:///D:/SiliCad/or_Gate/verification/coverage/final/final_code.rpt)
- **JasperGold Formal Log**: [jaspergold_formal.log](file:///D:/SiliCad/or_Gate/formal/jaspergold_formal.log)
