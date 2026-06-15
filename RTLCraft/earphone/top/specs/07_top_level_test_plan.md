# Earphone SoC - Top-Level Verification Test Plan

| Field | Value |
|-------|-------|
| Document ID | EARPHONE-TOP-TP-001 |
| Status | Active |

## Scope

The top-level contract tests cover L3 architecture metadata, L4 structural
connectivity, L5 DSL wrapper instantiation, and L6 Verilog emission.

## Test Inventory

| Test ID | Layer | Objective |
|---------|-------|-----------|
| TOP-L3-001 | L3 ArchitectureIR | Required modules, APB slots, and invariants are present. |
| TOP-L4-001 | L4 StructuralIR | Required instances and top-level connections are represented. |
| TOP-L5-001 | L5 DSL | `EarphoneTop` instantiates and exposes expected external ports. |
| TOP-L6-001 | L6 Verilog | Verilog emitter returns `module earphone_top` with key ports. |

## Sign-Off Criteria

- `python -m pytest earphone/top -q` returns zero.
- No top-level contract layer reports missing tests.
- Any failure feeds back to `earphone/specs/flow_feedback.json` before approval.
