# JPEG Datapath Cookbook

This cookbook turns the current `jpeg_decoder/` work into a reusable
datapath-authoring guide for `rtlgen_x`.

It focuses on the patterns that showed up as real pressure points during the
JPEG bring-up:

1. signed fixed-point arithmetic that must agree across lowering, compiled sim,
   and emitted RTL
2. ROM/LUT-backed datapaths that carry semantic initialization data
3. transpose / reorder buffers that should still flatten and emit predictably
4. hierarchical stage chaining that should stay readable and regression-safe
5. mixed DSL + external Verilog packaging when emitted RTL depends on extra
   source files or memory init files

## Where To Start

The worked example lives in [jpeg_decoder/dsl_modules.py](/Users/yangfan/release/EDACraft-main/RTLCraft/jpeg_decoder/dsl_modules.py).

The most useful entry points are:

1. `JpegIdct8x8`: signed LUT-backed row/column iDCT with a transpose buffer
2. `JpegDequantZigzag`: reorder + coefficient datapath staging
3. `JpegDecoder`: end-to-end stage composition

Good first reruns are:

```bash
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_idct_basic.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_dequant_idct.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_verilog.py
```

## Pattern 1: Signed Fixed-Point Datapath

Use explicit signed intent at the arithmetic boundaries.

Recommended style from `JpegIdct8x8`:

1. keep storage widths explicit
2. cast storage reads with `.as_sint()` before multiply / compare
3. use `RoundShiftRight(...)` for signed round-then-shift behavior
4. clamp through signed compares before narrowing back to pixel width

Representative locations:

1. `_prod <<= self._sample.as_sint() * self._idct_lut_data.as_sint()`
2. `_scaled <<= RoundShiftRight(self._sum_next, IDCT_FRAC)`
3. `_final <<= self._scaled.as_sint() + Const(128, ...)`

This is the safest current pattern when the author wants Python, compiled C++,
and emitted RTL to agree without relying on implicit signedness.

## Pattern 2: LUT / ROM-Backed MAC

For cosine tables, coefficient tables, or other ROM semantics:

1. put the table in design-visible storage on `self`
2. make the initialization part of module semantics
3. treat different `init_data` / `init_file` contents as different leaf meaning

Current JPEG example:

1. `self._idct_mem = Memory(16, 64, "idct_mem", init_data=IDCT_TABLE)`
2. address generation stays explicit in wires on the module
3. the datapath reads the ROM through normal DSL memory reads

This now has two important closure properties in the stack:

1. executable lowering loads `init_file` content instead of silently zeroing it
2. `emit_design(...)` dedup no longer merges same-interface ROM leafs whose
   initialization differs

## Pattern 3: Transpose / Reorder Buffers

Use `Array(...)` or `Memory(...)` as module-owned storage, not host-local
temporaries.

JPEG examples:

1. `self._block = Array(coeff_width, 64, "block")`
2. `self._tbuf = Array(16, 64, "tbuf")`
3. `ZIGZAG_ORDER` / `INV_ZIGZAG` drive reorder intent explicitly in Python-side
   table construction

Recommended authoring rules:

1. register the buffer on `self` so lint / lowering / flattening can see it
2. keep address calculation in named wires or regs on `self`
3. prefer one visible write index wire for transpose writes
4. prefer one visible sample-read wire for row/column mode switching

This makes hierarchy flattening and diagnostics much easier to trust.

## Pattern 4: Hierarchical Stage Chaining

For JPEG-like multi-stage datapaths, connect stage boundaries with explicit
parent-owned wires.

Good shape:

1. child output lands on a parent wire
2. the next child reads that parent wire
3. top-level output is driven from the final child boundary

The repo regression now locks a simple three-stage chain in
[rtlgen_x/tests/test_dsl_import.py](/Users/yangfan/release/EDACraft-main/RTLCraft/rtlgen_x/tests/test_dsl_import.py).

This is not a full handshake pipeline example, but it does cover the main
hierarchical risk: multiple child stages connected through parent-owned
intermediate wires still lower and emit correctly.

## Pattern 5: Mixed DSL + External Verilog Packaging

When a DSL top contains external Verilog leafs or ROM `init_file` storage,
emitted RTL is not self-contained unless those artifacts are staged together.

Current supported packaging metadata comes from:

```python
collect_external_verilog_artifacts(module)
```

It now gathers:

1. `sources`
2. `include_dirs`
3. `defines`
4. `init_files`

And the cosim staging path now carries those artifacts into local or remote
external-simulator build roots so that:

1. external blackbox implementations are compiled with the emitted DSL RTL
2. include trees and `+define+...` flags are preserved
3. ROM `init_file` payloads travel with the emitted `$readmemh(...)` design

Recommended usage rule:

1. if a module's emitted RTL depends on a file at runtime or compile time,
   assume it must be present in the packaging bundle too

## Rerun / Debug Loop

For a JPEG-style datapath change, the recommended loop is:

1. rerun one focused Python/executable regression first
2. rerun the emitted RTL smoke test once the executable path is stable
3. only then widen back out to larger integration coverage

Practical order:

```bash
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_idct_basic.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_dequant_idct.py
PYTHONPATH=. pytest -q rtlgen_x/tests/test_dsl_import.py -k 'init_file or child_output or hierarchical'
PYTHONPATH=. pytest -q rtlgen_x/tests/test_cosim.py -k 'cosim'
```

When debugging:

1. if Python/executable and emitted RTL disagree on ROM behavior, inspect
   `init_data` / `init_file` first
2. if signed math disagrees, inspect missing `.as_sint()` / `.as_uint()` and
   missing `RoundShiftRight(...)`
3. if hierarchy breaks, inspect whether parent-visible stage wires or storage
   were accidentally left as host-local temporaries

## Current Boundaries

This cookbook is intentionally scoped to the current closed subset.

Safe today:

1. comb-read ROM/LUT datapaths
2. explicit signed fixed-point authoring
3. transpose/reorder storage owned by the module
4. hierarchical child-output chaining through parent wires
5. mixed-design packaging for external RTL sources and ROM init files

Still explicit fail-fast rather than fully supported:

1. generic multi-port memories
2. arbitrary non-zero read latency storage contracts
3. broad sync-read RAM semantics beyond the currently narrowed subset
