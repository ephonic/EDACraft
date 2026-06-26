# Design Decision Log

## DEC-RV32-001: Divider implementation
- **Layer**: ArchitectureIR
- **Owner**: ai
- **Decision**: Use 32-cycle iterative restoring divider for DIV/DIVU/REM/REMU
- **Rationale**: Reduce divider area vs combinational implementation; acceptable latency for Earphone control code.
- **Alternatives**: Combinational divider, Radix-4 SRT divider
- **Impacted constraints**: EARP-RV32-001, EARP-RV32-002

## DEC-RV32-002: Pipeline clock gating
- **Layer**: ArchitectureIR
- **Owner**: ai
- **Decision**: Gate pipeline registers with core_clk_en = ~core_stall & ~muldiv_busy
- **Rationale**: Cut dynamic power during memory stalls and divide operations with minimal control overhead.
- **Alternatives**: Per-register fine-grained gating, Module-level clock gate only
- **Impacted constraints**: EARP-RV32-002

## DEC-SIMD-001: SIMD datapath gating
- **Layer**: ArchitectureIR
- **Owner**: ai
- **Decision**: Independent int_ce and fp_ce clock enables for INT16/FP16 datapaths
- **Rationale**: FP16 MAC pipeline toggles only when FP16 workloads are active; INT16 audio path remains active.
- **Alternatives**: Shared SIMD clock enable, Per-lane clock gating
- **Impacted constraints**: EARP-SIMD-001
