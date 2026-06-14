# 09 Constraint Traceability Report

## Constraints by Layer

| UID | Name | Category | Layer | Target | Owner | Derived From |
|-----|------|----------|-------|--------|-------|--------------|
| EARP-RV32-001_B_C_A | RV32M_DIV_ZERO_ARCH | functional | ArchitectureIR | EarphoneRV32.execute_stage | ai | EARP-RV32-001_B_C |
| EARP-RV32-002_B_C_A | CPU_CLK_GATE_STALL | power | ArchitectureIR | EarphoneRV32.pipeline_registers | ai | EARP-RV32-002_B_C |
| EARP-SIMD-001_B_C_A | SIMD16_VADD_OVERFLOW_ARCH | functional | ArchitectureIR | EarphoneSIMD16.int_alu | ai | EARP-SIMD-001_B_C |
| EARP-RV32-001_B | RV32M_DIV_ZERO_behavior | functional | BehaviorIR | RV32IM_ISS | ai | EARP-RV32-001 |
| EARP-RV32-002_B | CPU_PREFER_ITERATIVE_ALGORITHMS | functional | BehaviorIR | EarphoneRV32 | ai | EARP-RV32-002 |
| EARP-SIMD-001_B | SIMD16_VADD_OVERFLOW_behavior | functional | BehaviorIR | simd16_int16_functional | ai | EARP-SIMD-001 |
| EARP-RV32-001_B_C | RV32M_DIV_LATENCY | performance | CycleIR | EarphoneRV32.muldiv_busy | ai | EARP-RV32-001_B |
| EARP-RV32-002_B_C | CPU_STALL_DURING_MULTICYCLE_OPS | functional | CycleIR | EarphoneRV32.core_stall | ai | EARP-RV32-002_B |
| EARP-SIMD-001_B_C | SIMD16_VADD_LATENCY | performance | CycleIR | EarphoneSIMD16 | ai | EARP-SIMD-001_B |
| EARP-RV32-001_B_C_A_S_D | RV32M_DIV_ZERO_SEQ | verification | DSL | EarphoneRV32 | ai | EARP-RV32-001_B_C_A_S |
| EARP-RV32-002_B_C_A_S_D | CPU_CLK_GATE_CODING_STYLE | power | DSL | EarphoneRV32 | ai | EARP-RV32-002_B_C_A_S |
| EARP-SIMD-001_B_C_A_S_D | SIMD16_VADD_OVERFLOW_SVA | verification | DSL | EarphoneSIMD16 | ai | EARP-SIMD-001_B_C_A_S |
| EARP-RV32-001 | RV32M_DIV_ZERO | functional | SpecIR | EarphoneRV32 | human | — |
| EARP-RV32-002 | CPU_ACTIVE_POWER | power | SpecIR | EarphoneRV32 | human | — |
| EARP-RV32-003 | CPU_POWER_BUDGET_STRICT | power | SpecIR | EarphoneRV32 | human | — |
| EARP-SIMD-001 | SIMD16_VADD_OVERFLOW | functional | SpecIR | EarphoneSIMD16 | human | — |
| EARP-RV32-001_B_C_A_S | RV32M_DIV_ZERO_STRUCT | functional | StructuralIR | EarphoneRV32.execute_agent | ai | EARP-RV32-001_B_C_A |
| EARP-RV32-002_B_C_A_S | CPU_ICG_INSERTION | power | StructuralIR | EarphoneRV32 | ai | EARP-RV32-002_B_C_A |
| EARP-SIMD-001_B_C_A_S | SIMD16_VADD_OVERFLOW_STRUCT | functional | StructuralIR | EarphoneSIMD16.monitor | ai | EARP-SIMD-001_B_C_A |
| EARP-RV32-001_B_C_A_S_D_V | RV32M_DIV_ZERO_UVM | verification | Verilog | EarphoneRV32 | ai | EARP-RV32-001_B_C_A_S_D |
| EARP-RV32-002_B_C_A_S_D_V | CPU_ACTIVE_POWER_REPORT | power | Verilog | EarphoneRV32 | ai | EARP-RV32-002_B_C_A_S_D |
| EARP-SIMD-001_B_C_A_S_D_V | SIMD16_VADD_OVERFLOW_SVA_VERILOG | verification | Verilog | EarphoneSIMD16 | ai | EARP-SIMD-001_B_C_A_S_D |

## Generated Artifacts

| Artifact | Source Constraint |
|----------|-------------------|
| rv32_div_zero_seq.sv | RV32M_DIV_ZERO_UVM |
| cpu_power_report.md | CPU_ACTIVE_POWER_REPORT |
| simd16_vadd_overflow_sva.sv | SIMD16_VADD_OVERFLOW_SVA_VERILOG |