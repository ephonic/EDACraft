# RTLCraft Project Status

> Last updated: 2026-05-30

---

## Project Overview

RTLCraft is a Python DSL-to-Verilog RTL generation framework with a white-box AST architecture. The key differentiator from HLS tools: **fully transparent AST** — every Signal, Module, and Assign is an explicit node that can be inspected, traversed, and modified.

---

## Architecture

```
Spec → Arch Planner → Skeleton → DSL Generation → AST → Verilog/SV
                                                    ↓
                                              Simulation
                                              PPA Analysis
                                              Lint/SMT/ABC
```

Three abstraction layers:
1. **Behavioral** — CycleContext functions, golden reference traces
2. **Skeleton** — Sub-module decomposition, port specs, interconnection maps
3. **DSL** — Python code building AST nodes, then emitted to Verilog

---

## Active Development Focus: riscv64_soc Skill

### Current Output State

| Artifact | Count | Location |
|----------|-------|----------|
| Behavioral specs (Markdown) | 384 | `generated_skill_ppa/riscv64_soc/specs/` |
| Verilog RTL | 385 | `generated_skill_ppa/riscv64_soc/*.v` |
| Hand-written DSL (Python) | 3 | `generated_skill_ppa/riscv64_soc/code/` |
| PE types | 6 | Core, L1I, L1D, NoCRouter, CoherenceDir, L2Slice |
| PE instances | 64 | 8×8 mesh (0–63) |

### Hand-written DSL Modules

| File | Module | Features | Sim Status |
|------|--------|----------|------------|
| `Core_0.py` | RV64Core | 5-stage pipeline, 3-stage forwarding (EX/MEM/WB), load-use hazard stall, all RV64I branches, retire counter | ✅ PASS (NOP stream: 195 retired in 200 cycles) |
| `L1I_0.py` | L1ICache | Direct-mapped, tag/data RAM, MSI state, refill FSM (IDLE→REFILL→DELIVER) | ✅ PASS (miss/refill/hit verified) |
| `NoCRouter_0.py` | NoCRouter | 5-port (N/S/E/W/J), XY routing, 4-deep input FIFOs, priority arbitration (N>S>E>W>J) | ✅ PASS (15/15 tests) |

### What's Missing

- **DSL files only for instance 0** — instances 1–63 have no hand-written DSL code. All 385 Verilog files exist but were generated from the skeleton template, not from hand-written DSL.
- **L1D, CoherenceDir, L2Slice** — no hand-written DSL yet (3 remaining PE types).
- **Cross-module integration test** — Core + L1I + NoCRouter + L2Slice have not been simulated together as a subsystem.

---

## Recent Code Changes

### 1. Core_0: Pipeline "last-write-wins" fix

**Problem**: The DSL simulator evaluates `seq` blocks sequentially — multiple independent `If/Elif` blocks writing to the same register means the last assignment overwrites earlier ones. Pipeline valid registers were being zeroed by later branches.

**Fix**: Restructured from multiple parallel `If/Elif` blocks to a unified `seq` block with comb-computed transition control signals (`f_to_d`, `d_to_e`, `e_to_m`, `m_to_w`, `fetch_new`). Each register is written exactly once per cycle.

### 2. NoCRouter_0: Push logic forward-reference fix

**Problem**: Internal ready wires (`n_ready_int` etc.) were defined in the `comb` block but referenced in the `seq` block. Due to evaluation order, they were always 0 during push condition checks.

**Fix**: Replaced wire references with direct buffer count comparisons in the seq block: `(e_buf_count < 4)` instead of `e_ready_int`.

### 3. Reset compliance across all modules

All modules gate non-zero outputs behind an `init` register (`pipeline_active`, `cache_init`, `router_init`) that stays 0 until the first valid operation completes.

---

## Framework Improvements

### dsl_parser.py: Added `load_dsl_module()` for direct import

DSL files are plain Python — no separate DSL text format exists. Added `load_dsl_module(filepath)` that uses `importlib` to directly import DSL files as regular Python modules. This replaces the `exec`-based `parse_dsl_code()` for file-based loading (kept for LLM-generated markdown responses).

### core.py: Lazy re-exports to fix circular imports

`rtlgen.logic` imports `Module` from `rtlgen.core`, so adding `from rtlgen.logic import If, Else, ...` at the top of `core.py` caused a circular import. Fixed by:

- **Lazy `__getattr__`**: `If`, `Else`, `Elif`, `Switch`, `Cat`, `Rep`, `SRA` are imported on-demand via `__getattr__`, avoiding circular import at module load time.
- **Mux width auto-inference**: `core.Mux` class now accepts optional `width` parameter (auto-infers from operand widths if omitted), making it compatible with the function form in `rtlgen.logic`.

---

## Key Bug Patterns Discovered

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| Pipeline signals stuck at 0 | DSL sim "last write wins" — multiple seq If blocks to same register | Unified transition control signals, single write per register |
| Reset test failures (outputs ≠ 0) | Combinational outputs driven even before first operation | `init` register gating |
| NoCRouter push never fires | comb wires used in seq conditions, evaluated before assignment | Direct comparison in seq, no intermediate wires |
| `rst_n` not released in sim | `sim.reset()` uses default `rst="rst"` but signal is `rst_n` | Pass `rst="rst_n"` explicitly |
| `Mux` requires explicit width | `core.Mux` is a class (4 args), `logic.Mux` is a function (3 args, auto-width) | Made `core.Mux.width` optional with auto-inference |
| Circular import core ↔ logic | `core.py` imports from `logic.py` which imports `Module` from `core.py` | Lazy `__getattr__` re-exports |
| Module instantiation fails | Parser calls `cls(name=...)` but some modules don't accept name kwarg | Try/except fallback to `cls()` |

---

## Pending Work

### High Priority
1. **Write DSL for remaining PE types** — L1D (L1 Data Cache), CoherenceDir (Coherence Directory), L2Slice (L2 Cache Slice)
2. **Batch DSL generation for all 64 instances** — currently only instance 0 has hand-written code
3. **Subsystem integration test** — Core + L1I + NoCRouter + L2 in a 2×2 mesh simulation

### Medium Priority
4. **Fix `sim.reset()` auto-detection** — should detect `rst_n` automatically instead of requiring `rst="rst_n"`
5. **NoCRouter multi-cycle throughput** — currently 5/10 cycles, should approach 1:1 for streaming traffic
6. **PPA analysis on hand-written DSL** — compare skeleton RTL vs hand-written DSL for area/timing

### Low Priority
7. **Remove `dsl_parser.parse_dsl_code` exec path** — if all loading uses `load_dsl_module`, the exec path is only needed for LLM responses
8. **Verilog emission verification** — ensure hand-written DSL emits correct Verilog (already works for Core_0, verify for L1I_0 and NoCRouter_0)

---

## How to Run

```bash
# Skill-guided pipeline (requires Claude API key)
python -m rtlgen.skill_ppa --skill riscv64_soc

# Simulate hand-written DSL modules
python sim_noc_router.py     # NoCRouter_0 (15 tests)
python sim_gfsk              # GFSK modulation (iverilog)
python sim_hetero_test       # Hetero RISC-V mesh (iverilog)
```

---

## File Map (Key Files)

| File | Purpose |
|------|---------|
| `rtlgen/core.py` | Signal/Module/AST base classes |
| `rtlgen/logic.py` | If/Else/Switch/Mux/Cat/Rep DSL constructs |
| `rtlgen/dsl_parser.py` | Direct import + exec-based parsing |
| `rtlgen/sim.py` | AST interpreter simulator |
| `rtlgen/codegen.py` | AST → Verilog emitter |
| `rtlgen/skill_ppa.py` | Pipeline orchestrator (behaviors→rtl→lint) |
| `rtlgen/gen_requirement.py` | GenerationContext, ModuleRequirement |
| `rtlgen/reference_extractor.py` | Code snippet extraction from skills |
| `rtlgen/arch_skel.py` | Sub-module decomposition |
| `rtlgen/arch_def.py` | PE model, CycleContext |
| `rtlgen/dsl_sim.py` | Simulation-based DSL validation |
| `rtlgen/verifier.py` | 4-level verification + repair loop |
| `generated_skill_ppa/riscv64_soc/code/Core_0.py` | Hand-written RV64Core DSL |
| `generated_skill_ppa/riscv64_soc/code/L1I_0.py` | Hand-written L1 I-Cache DSL |
| `generated_skill_ppa/riscv64_soc/code/NoCRouter_0.py` | Hand-written NoC Router DSL |
