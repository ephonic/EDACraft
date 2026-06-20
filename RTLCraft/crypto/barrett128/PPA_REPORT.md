# PPA Analysis & Optimization Report — 128-bit Barrett Modular Multiplier

**Date:** 2026-06-20  
**Module:** `barrett_mod_mul` (`crypto/barrett128/`)  
**Tool:** `rtlgen_x.ppa`

---

## 1. Design summary

Current RTL is the **Karatsuba-Ofman (KO)** version of the Barrett multiplier.
The original flat 64-limb schoolbook multiply was replaced with a 3-level KO
tree that keeps throughput at 1 op/cycle while reducing combinational depth.

The pipeline now has **8 registered stages**:

| Stage | Operation |
|-------|-----------|
| S0 | 27 KO leaf multiplies (`16x16` .. `19x19`) |
| S1 | 9 KO level-1 combines |
| S2 | 3 KO level-2 combines |
| S3 | final `256-bit` product `p_q` |
| S4 | Barrett quotient estimate |
| S5 | Barrett residual |
| S6 | first conditional subtract |
| S7 | second conditional subtract / final result |

Latency is **7 cycles**, throughput remains **1 op/cycle**.

---

## 2. Module-side structural analysis

Current `analyze_module_ppa(BarrettModMul())` reports:

| Metric | Value |
|--------|-------|
| `module_name` | `barrett_mod_mul` |
| `state_bits` | **4906** |
| `memory_bits` | 0 |
| `comb_assignments` | 3 |
| `seq_assignments` | 64 |
| `max_expr_depth` | **22** |
| `critical_assignment_target` | `p16_MMM` |
| `critical_expr_op` | `*` |
| `critical_expr_operand_widths` | `(19, 19)` |

Interpretation:

1. The KO restructure cut critical expression depth from the prior schoolbook
   cone (72) down to **22**.
2. The deepest remaining path is the **`p16_MMM` leaf multiply**, where three
   nested `(hi + lo)` adders feed a `19x19` multiply.
3. State cost increased because the design now stores KO partial products
   across 4 multiplier stages plus the delayed `n/m` sideband and Barrett tail.

---

## 3. PPA guidance

For `PpaGoals(priority="timing_first", max_logic_depth=8)`, the advisor flags:

- **High:** Pipeline or rebalance deep combinational logic
- **Medium:** Reduce or gate large sequential state

The timing recommendation now points directly at the KO hotspot:

- target: `p16_MMM`
- phase: `seq`
- source: `crypto/barrett128/dsl.py`
- operator: `*`
- operand widths: `19 x 19`

This is the right place for any next timing pass.

---

## 4. Architecture-side throughput model

The architecture-side model should now be interpreted as an **8-stage**
throughput-1 pipeline:

`ko_leaf -> ko_lvl1 -> ko_lvl2 -> ko_final -> qest -> resid -> csub0 -> csub1`

With `latency=1`, `initiation_interval=1`, `capacity=1` on every stage:

- steady-state throughput stays near **1.0 op/cycle**
- queue pressure remains low at the current test settings

So the KO rewrite traded **latency and state** for **timing depth**, not for
throughput.

---

## 5. Verification status

Current KO RTL is verified through:

1. bundled Python sim directed tests
2. bundled Python sim back-to-back stream tests
3. emitted RTL compile under `iverilog`
4. directed `iverilog` cosim
5. streamed `iverilog` cosim
6. Python-UVM and generated SV/UVM collateral smoke tests

The `iverilog` stream testbench now sizes `expected[]` from `len(vecs)`, so
longer streams are no longer capped by the old fixed 256-entry array.
The cosim helper also emits per-run unique RTL / TB / `.vvp` artifact names, so
repeated or parallel probes do not clobber each other in the shared build
directory.

---

## 6. Remaining work

The main open PPA item is still the KO leaf stage:

1. **Leaf depth 22 is still above the target budget 8.**  
   To go lower, the `(hi + lo)` sum tree in the `M-M-M` path needs its own
   register cut before the `19x19` multiply.

2. **State footprint is intentionally larger.**  
   Some width-tightening is still possible, but this is secondary to the timing
   objective.

3. **Framework reporting is better, but still shallow.**  
   The PPA tool now reports the hotspot assignment, file/line, operator, and
   operand widths. It still does not infer multiplier-family-specific advice on
   its own.
