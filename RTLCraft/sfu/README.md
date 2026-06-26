# FP16 SFU example

This directory contains a worked example of a fully pipelined scalar FP16
special-function unit built on the legacy DSL and validated through the
`rtlgen_x` execution stack.

## What this example implements

`Fp16Sfu` in [dsl.py](./dsl.py) is a throughput-1, latency-5 pipeline with:

1. `relu`
2. `sigmoid`
3. `tanh`
4. `sin`
5. `cos`

The nonlinear functions use second-order piecewise interpolation:

1. `sigmoid`: `|x|` over `[0, 8]`
2. `tanh`: `|x|` over `[0, 4]`
3. `sin/cos`: quadrant-reduced `[0, pi/2]`

All interpolation tables are generated in Python and shared by both the golden
reference and the RTL-facing design model.

## File layout

1. [dsl.py](./dsl.py): pipelined legacy-DSL implementation
2. [reference.py](./reference.py): bit-accurate scalar golden model
3. [lut_generator.py](./lut_generator.py): quadratic coefficient table builder
4. [driver.py](./driver.py): reset, single-shot, and streaming helpers
5. [tests/test_functional.py](./tests/test_functional.py): end-to-end regression

## Why this example matters

This example is intentionally a little more demanding than the earlier toy
designs. It exercises several framework properties at once:

1. ROM-style memories with signed `init_data`
2. piecewise coefficient lookup
3. signed multiply followed by arithmetic right shift
4. dependent combinational wiring chains across multiple blocks
5. bubble-safe pipelined valid propagation

During bring-up, it exposed real framework gaps that are now closed:

1. `Memory(..., init_data=...)` now reaches emitted RTL and lowered `SimModule`
   execution
2. `SRA(...)` now round-trips cleanly through lowering, simulation, and Verilog
   emission
3. lowered combinational assignments are topologically ordered before execution
4. lowered multiply width inference preserves full product width

## Validation flow

Recommended local checks:

```bash
python -m pytest sfu/tests/test_functional.py -q
python -m pytest rtlgen_x/tests/test_dsl_legacy_import.py sfu/tests/test_functional.py -q -rA
python sfu/iverilog_cosim.py
```

The regression covers:

1. directed reference vectors
2. lowered `SimModule` behavior through `PythonSimulator`
3. emitted RTL compile under `iverilog`
4. directed emitted-RTL cosim
5. small-stream emitted-RTL cosim
6. random streaming behavior over mixed operations
7. emitted RTL structure checks

## Current emitted-RTL closure

The practical emitted-RTL closure for this DUT is:

1. `VerilogEmitter().emit(Fp16Sfu())`
2. compile under `iverilog`
3. run the dedicated `sfu/iverilog_cosim.py` streaming harness

That harness is the right closure path for this DUT because it understands the
`in_valid/out_valid` streaming contract and checks results only when `out_valid`
asserts.

There is also a generic helper in `rtlgen_x.sim.run_legacy_rtl_cosim(...)`, but
it now supports valid-gated streaming parity through `valid_signal`,
`flush_cycles`, and `flush_inputs`.

The dedicated SFU harness is still useful because it gives a DUT-shaped place
to add richer protocol checks, custom scoreboarding, and larger randomized
streams without stretching the generic helper.

## Current PPA readout and tradeoffs

`analyze_module_ppa(Fp16Sfu())` currently reports, at a high level:

1. `state_bits = 572`
2. `memory_bits = 6912`
3. `memory_count = 4`
4. `small_memory_count = 4`
5. `max_memory_width = 54`
6. `multiplier_ops = 118`
7. widest multiply site at `trig_t_q12_w`

What that means in practice:

1. the LUT footprint is not huge, but the tables are shallow and fetched in
   lock-step, so packing `c0/c1/c2` into one ROM word is a good structural
   default
2. the current 6-stage pipeline is not obviously over-pipelined; if anything,
   the trig-reduction and polynomial stages remain the main timing pressure
3. blindly shrinking stage count is likely the wrong move before the wide
   multiply chains are reduced
4. the next real timing/energy tradeoff is probably in multiplier structure,
   not in adding more table depth

## Design flow used here

The practical loop for this SFU is:

```text
LUT/reference model
  -> legacy DSL pipeline
  -> lowered executable model
  -> Python simulator regression
  -> emitted Verilog / downstream verification collateral
```

This is the style we want `rtlgen_x` to support well: the agent writes the
design directly, the framework makes it executable quickly, and verification and
feedback happen against runnable artifacts rather than against a heavy
document-control layer.
