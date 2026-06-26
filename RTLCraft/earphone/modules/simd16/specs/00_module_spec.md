# EarphoneSIMD16 — Module Design Specification

| Document ID | SIMD16-MOD-001 |
|-------------|--------------|
| Version     | 0.1 |
| Date        | 2026-06-18 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Module ID   | SIMD16 |
| Status      | Draft |

---

## 1. Overview

### 1.1 Purpose
16-lane SIMD accelerator: 1-cycle INT16 ALU + 3-stage FP16 MAC with per-lane predicate masking.

### 1.2 Features
| ID | Feature | Description |
|----|---------|-------------|
| F-01 | ISA / protocol compliance | Implements the target instruction set or interface protocol. |
| F-02 | Power/area optimization | Tuned for earphone-class low-power constraints. |

### 1.3 Use Cases
Used inside the Smart Earphone SoC as the EarphoneSIMD16 block.

### 1.4 Block Diagram

See layer_L4_structure/specs/04_structural_spec.md for the internal decomposition of EarphoneSIMD16.

```text
+-----------------------------------------------------------+
|                     EarphoneSIMD16                        |
|  +----------------+        +---------------------------+  |
|  | Control |------->| Datapath            |  |
|  +----------------+        +---------------------------+  |
+-----------------------------------------------------------+
```

---

## 2. References

| Document ID | Title | Version | Description |
|-------------|-------|---------|-------------|
| EARPHONE-SOC-SPEC | Smart Earphone SoC Design Specification | 0.1 | Top-level requirements, architecture, PPA targets, and roadmap. |

---

## 3. Definitions and Abbreviations

| Term | Definition |
|------|------------|
| IR | Intermediate representation used for staged Spec2RTL lowering. |

---

## 4. Interface Definition

### 4.1 Port List

#### Clock and Reset
| Port Name | Width | Direction | Description |
|-----------|-------|-----------|-------------|
| clk | 1 | Input | System clock |
| rst_n | 1 | Input | Active-low asynchronous reset, synchronous release |

#### Functional Ports
| Port Name | Width | Direction | Protocol / Encoding | Description |
|-----------|-------|-----------|---------------------|-------------|
| Top-level interface group | module-specific | Input/Output | module-local protocol | See per-layer specs for detailed port lists. |

### 4.2 Interface Timing

Layer-specific timing assumptions are captured in the L2 CycleIR and L3 ArchitectureIR specs.

### 4.3 Protocol Compliance
| Protocol | Version | Compliance Level | Notes |
|----------|---------|------------------|-------|
| Module-local protocol | 0.1 | Project-defined | Detailed port semantics are defined in the L5 DSL spec and generated Verilog. |

---

## 5. Parameters and Configuration

| Parameter Name | Type | Default | Range | Description |
|----------------|------|---------|-------|-------------|
| Module parameters | contract | See L3/L5 specs | module-specific | Configuration captured in layer contracts rather than free-form template text. |

---

## 6. Functional Description

### 6.1 Theory of Operation
EarphoneSIMD16 operation is described per-IR-layer in the layer_L*/specs/ documents.

### 6.2 State Machine(s)

| State | Encoding | Description | Exit Conditions |
|-------|----------|-------------|-----------------|
| Operational | implementation-defined | Normal active state for EarphoneSIMD16. | Reset, stall, or module-specific completion. |

### 6.3 Data Path
See L4 StructuralIR spec.

### 6.4 Error Handling
| Error Condition | Detection | Response | Reporting |
|-----------------|-----------|----------|-----------|
| Invalid or unsupported transaction | Protocol decode or functional guard | Ignore, return safe value, or assert module-specific error status | Layer tests and generated verification reports |

---

## 7. Microarchitecture

### 7.1 Major Sub-blocks
| Sub-block | Description | Interface |
|-----------|-------------|-----------|
| Control / Datapath | Module-specific control and datapath partition. | See L4 StructuralIR contract. |

### 7.2 Pipeline Stages
| Stage | Latency | Description |
|-------|---------|-------------|
| Layer-defined | Layer-defined | Pipeline and latency details are defined in L2/L3 contracts. |

### 7.3 Critical Path Considerations
Tracked through L5 DSL lint/PPA analysis and L6 Verilog reports.

---

## 8. Timing

### 8.1 Clocking
| Clock Name | Frequency | Source | Notes |
|------------|-----------|--------|-------|
| clk | 48-160 MHz target | clk_sys | Earphone-class low-power system clock domain. |

### 8.2 Reset
| Reset Name | Type | Active Level | Description |
|------------|------|--------------|-------------|
| rst_n | asynchronous assert, synchronous release | active low | Resets architectural and control state to layer-specified defaults. |

### 8.3 Timing Diagrams

See L2 CycleIR test plan and cross-layer traces.

---

## 9. Registers

### 9.1 Register Summary
| Address Offset | Register Name | Width | Access | Reset Value | Description |
|----------------|---------------|-------|--------|-------------|-------------|
| N/A | Internal state | module-specific | internal | layer-specified | State elements are listed in L1/L2/L5 specs. |

### 9.2 Register Detail

#### Internal state
| Bit | Field | Access | Reset | Description |
|-----|-------|--------|-------|-------------|
| N/A | N/A | N/A | N/A | No externally visible register field described at this level. |

---

## 10. Power Management

### 10.1 Power Domain
clk_sys low-power domain unless the module spec states otherwise.

### 10.2 Clock Gating
| Clock Enable Signal | Controlled Logic | Idle Behavior |
|---------------------|------------------|---------------|
| module clock enable | state registers and datapath flops | hold state and suppress unnecessary switching |

### 10.3 Low-Power Modes
| Mode | Entry | Exit | Impact |
|------|-------|------|--------|
| idle | no active request or layer-specific stall | new request, interrupt, or reset release | reduced dynamic switching |

---

## 11. Verification Considerations

### 11.1 Verification Strategy
L1 behavior tests → L2 cycle tests → L3 DSL tests → L6 Verilog tests.

### 11.2 Key Verification Points
| ID | Check | Method | Coverage Goal |
|----|-------|--------|---------------|
| V-01 | Functional equivalence across layers | Cross-layer verification via LayerVerifier | 100% of ISA/protocol operations |

### 11.3 Assertions
| ID | Assertion | Severity | Description |
|----|-----------|----------|-------------|
| A-01 | Layer contract invariants hold during active operation | error | Assertions are generated from verification intents and constraints. |

---

## 12. Design Constraints and Assumptions

### 12.1 Constraints
| ID | Constraint | Source |
|----|------------|--------|
| C-01 | Module specification compliance | Top-level SoC spec and layer contracts |

### 12.2 Assumptions
| ID | Assumption | Rationale |
|----|------------|-----------|
| A-01 | Little-endian data representation unless specified otherwise | Matches RV32/APB memory semantics in the Earphone SoC. |

---

## 13. Synthesis and Implementation Notes

### 13.1 Synthesis Target
| Item | Target |
|------|--------|
| Technology | 22nm / 28nm low-power CMOS target |
| Frequency | 48-160 MHz |
| Area Goal | module-specific PPA budget |

### 13.2 Tool Settings
rtlgen VerilogEmitter, VerilogLinter, and optional downstream synthesis feedback.

---

## 14. Deliverables

| ID | Deliverable | Format | Owner |
|----|-------------|--------|-------|
| D-01 | simd16 layer contracts, source, tests, reports, and generated RTL where applicable | Markdown, JSON, Python, Verilog | RTLCraft Agent |

---

## 15. Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-06-18 | RTLCraft Agent | Initial draft. |
