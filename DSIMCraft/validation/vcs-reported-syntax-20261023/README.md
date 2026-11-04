# VCS verification of reported syntax gaps

Executed on `yangfan@10.131.254.103`, after sourcing `/apps/EDAs/syn.bash`,
on 2026-10-23. Actual compiler/runtime: **VCS W-2024.09_Full64**.
These are compilation and simulation results, not documentation-based assumptions.

| Probe | Flags | Actual result |
| --- | --- | --- |
| Packed two-dimensional module ports, byte and bit indexing | `-full64 -sverilog` | PASS; `a=12a5 y=a6ed byte=ed bit=1` |
| Generate loops using `i++`, `++j`, `k--` | `-full64 -sverilog` | PASS; all three generated vectors equal `a` |
| Root named `matvec_tb`, child declared first, no `-top` | `-full64 -sverilog` | PASS; correct root executes |
| Same root explicitly selected | `-full64 -sverilog -top matvec_tb` | PASS |
| Unescaped ordinary identifier `ref` | `-full64 -sverilog` | Expected rejection, exit 255; syntax error at `ref` |
| Escaped identifier `\ref ` | `-full64 -sverilog` | PASS; value 7 |
| Unescaped ordinary identifier `ref`, source copied to `.v` | `-full64`, without `-sverilog` | PASS; value 7 |

Thus packed ports, generate increments and automatic root selection are confirmed
dsim compatibility gaps. Reserving `ref` in SystemVerilog agrees with VCS.
The Verilog-mode acceptance is a language-mode difference: it does not justify
removing `ref` from the SystemVerilog keyword set.

All seven expected outcomes passed. Positive probes verify actual values using
assertions and TRACE output. [Results](results/results.json) record exact commands,
source SHA-256 values, exit codes and traces. Each case directory retains its
compile log and, where compilation succeeded, run log. `run.py` reproduces the
checks in a VCS-configured shell; no proprietary executables are archived.

[Local before-state](dsim-before.json) records the same inputs with the current
development dsim compiler and `--emit-only`: packed ports, generate increments,
implicit root selection and the unescaped SystemVerilog `ref` fail; the escaped
identifier succeeds. This local check covers elaboration only and does not claim
simulation alignment or any fixes to the three confirmed gaps.
