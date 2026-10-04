# or_gate Microarchitectural & Verification Specification

## 1. Architectural Overview
The `or_gate` is a fundamental combinational digital logic component that computes the logical OR between two single-bit inputs `a` and `b`.

### Truth Table
| Input `a` | Input `b` | Output `out` | Comment |
|:---:|:---:|:---:|:---|
| 0 | 0 | 0 | Both inputs low |
| 0 | 1 | 1 | Input `b` active |
| 1 | 0 | 1 | Input `a` active |
| 1 | 1 | 1 | Both inputs active |

## 2. Port Interface
| Signal Name | Direction | Width | Description |
|:---|:---:|:---:|:---|
| `a` | Input | 1 | Logic operand A |
| `b` | Input | 1 | Logic operand B |
| `out` | Output | 1 | Logical OR result ($a \lor b$) |

## 3. Timing and Delays
- Pure combinational logic. Output reacts instantaneously upon any input change.
- In testbench environment, interface signals are synchronously driven on `posedge clk` and sampled on `negedge clk` to guarantee race-free simulation.
