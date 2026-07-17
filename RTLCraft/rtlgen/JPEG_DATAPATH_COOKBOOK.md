# JPEG Datapath Cookbook

This cookbook turns the current `jpeg_decoder/` work into a reusable
datapath-authoring guide for `rtlgen`.

For the rerun-first worked-example view, start with
[../jpeg_decoder/README.md](../jpeg_decoder/README.md).
This cookbook stays focused on the reusable design patterns underneath that
example.

It focuses on the patterns that showed up as real pressure points during the
JPEG bring-up:

1. signed fixed-point arithmetic that must agree across lowering, compiled sim,
   and emitted RTL
2. ROM/LUT-backed datapaths that carry semantic initialization data
3. transpose / reorder buffers that should still flatten and emit predictably
4. hierarchical stage chaining that should stay readable and regression-safe
5. mixed DSL + external Verilog packaging when emitted RTL depends on extra
   source files or memory init files

For the dedicated mixed-design worked example and backend-selection guide, use
[MIXED_DESIGN_COSIM_GUIDE.md](./MIXED_DESIGN_COSIM_GUIDE.md). This cookbook
keeps the JPEG-side authoring patterns; the mixed-design guide keeps the
artifact-packaging and cosim migration story.

## Where To Start

The worked example lives in
[../jpeg_decoder/dsl_modules.py](../jpeg_decoder/dsl_modules.py).

The most useful entry points are:

1. `JpegIdct8x8`: signed LUT-backed row/column iDCT with a transpose buffer
2. `JpegDequantZigzag`: reorder + coefficient datapath staging
3. `JpegDecoder`: end-to-end stage composition

Good first reruns are:

```bash
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_idct_basic.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_cpp_idct.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_dequant_idct.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_cpp_entropy_dequant.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_verilog.py
```

Backend note:

1. Python and compiled simulator regressions are the primary functional closure
   path for the JPEG datapath today
2. `jpeg_decoder/tests/test_verilog.py` keeps `iverilog -g2012` as a compile
   smoke check for the emitted SystemVerilog subset
3. for fuller emitted-RTL closure, prefer the stronger RTL backends already
   wired into the repo (`verilator`, then `vcs` when available)

## Pattern Index

Use this table as the first jump point when authoring or debugging another
JPEG-like datapath.

| Pattern | Primary code anchor | Regression anchor | First thing to inspect when it breaks |
|---------|---------------------|-------------------|--------------------------------------|
| signed round + level shift + clip | `JpegIdct8x8` wires `_prod`, `_sum_next`, `_scaled`, `_final`, `_clipped` | `test_cpp_idct.py`, `test_dsl_round_shift_level_shift_and_clip_matches_compiled_simulator(...)` | missing `.as_sint()` before multiply/compare, or plain shift instead of `RoundShiftRight(...)` |
| LUT-backed MAC | `JpegIdct8x8._idct_mem`, `_idct_lut_addr`, `_idct_lut_data` | `test_idct_basic.py`, `test_cpp_idct.py` | ROM initialization, address packing, signed interpretation of LUT data |
| transpose buffer | `JpegIdct8x8._tbuf`, `_write_idx`, row/column mode sample select | `test_idct_basic.py`, `test_cpp_idct.py` | row/column index order and whether the write index is module-visible |
| zig-zag reorder | `JpegDequantZigzag._zz_lut`, `_zigzag_buf`, `_raster_idx`, `_zz_idx_wire` | `test_dequant_idct.py`, `test_cpp_entropy_dequant.py` | whether input order, raster order, and inverse-zig-zag LUT agree |
| stage handoff | `DequantIdctWrapper.dq_out`, `dq_out_valid`, `dq_out_ready` | `test_dequant_idct_wrapper_lowers_and_emits_parent_owned_handoff(...)` | parent-owned wires accidentally left as host-local `Wire(...)` temporaries |
| emitted RTL smoke | `jpeg_decoder/tests/test_verilog.py` | `test_jpeg_verilog_iverilog_compile_smoke(...)` | reserved names, SystemVerilog subset boundaries, backend policy |

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
4. `_clipped <<= Mux(_final.as_sint() < 0, 0, Mux(_final.as_sint() > 255, 255, _final))`

Keep the intermediate signals module-owned. That gives diagnostics, emitted
RTL naming, and simulator traces stable handles for the exact signed datapath
you are trying to debug.

This is the safest current pattern when the author wants Python, compiled C++,
and emitted RTL to agree without relying on implicit signedness.

The standalone regression for this contract is
`test_dsl_round_shift_level_shift_and_clip_matches_compiled_simulator(...)` in
[rtlgen/tests/test_dsl_import.py](./tests/test_dsl_import.py).
It covers negative intermediates, low/high clipping, and the neutral `+128`
level-shift path outside the full JPEG integration test.

## Pattern 2: LUT / ROM-Backed MAC

For cosine tables, coefficient tables, or other ROM semantics:

1. put the table in design-visible storage on `self`
2. make the initialization part of module semantics
3. treat different `init_data` / `init_file` contents as different leaf meaning

Current JPEG example:

1. `self._idct_mem = Memory(16, 64, "idct_mem", init_data=IDCT_TABLE)`
2. address generation stays explicit in wires on the module
3. the datapath reads the ROM through normal DSL memory reads

Authoring checklist:

1. keep the table payload in `init_data` or `init_file`, not in host-side
   control flow hidden from the DSL
2. keep address composition in named wires (`_lut_addr`, `_idct_lut_addr`) so
   lowering and emitted RTL are inspectable
3. cast the ROM data at the arithmetic use site if signed math is intended

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

Two distinct buffer patterns show up:

1. transpose writes row transform output into `_tbuf[col*8 + row]`, then column
   mode reads `_tbuf[col*8 + u]`
2. zig-zag reorder stores input coefficients in `_zigzag_buf[zigzag_index]`,
   then emits raster order by reading through `_zz_lut[raster_index]`

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

For ready/valid boundaries, the same rule applies to all three lanes:

1. payload, such as `dq_out`
2. valid, such as `dq_out_valid`
3. ready, such as `dq_out_ready`

These must be attributes on the parent module (`self.dq_out = Wire(...)`), not
temporary local `Wire(...)` values, so authoring-intent validation and
flattening agree on ownership.

The repo regression now locks a simple three-stage chain in
[rtlgen/tests/test_dsl_import.py](./tests/test_dsl_import.py).

The JPEG-shaped regression lives in
[../jpeg_decoder/tests/test_dequant_idct.py](../jpeg_decoder/tests/test_dequant_idct.py):

1. `test_dequant_idct_chain_matches_reference(...)` checks executable behavior
2. `test_dequant_idct_wrapper_lowers_and_emits_parent_owned_handoff(...)` checks
   lowering plus emitted RTL structure for the parent-owned handoff

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

And the cosim staging path now carries those artifacts into local
external-simulator build roots so that:

1. external blackbox implementations are compiled with the emitted DSL RTL
2. include trees and `+define+...` flags are preserved
3. ROM `init_file` payloads travel with the emitted `$readmemh(...)` design

Recommended usage rule:

1. if a module's emitted RTL depends on a file at runtime or compile time,
   assume it must be present in the packaging bundle too

The smallest regression-backed example for that rule is in
[rtlgen/tests/test_cosim.py](./tests/test_cosim.py),
and the walkthrough version now lives in
[MIXED_DESIGN_COSIM_GUIDE.md](./MIXED_DESIGN_COSIM_GUIDE.md).

## Rerun / Debug Loop

For a JPEG-style datapath change, the recommended loop is:

1. rerun one focused Python/executable regression first
2. rerun the emitted RTL smoke test once the executable path is stable
3. only then widen back out to larger integration coverage

Practical order:

```bash
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_idct_basic.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_cpp_idct.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_dequant_idct.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_cpp_entropy_dequant.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_verilog.py
PYTHONPATH=. pytest -q rtlgen/tests/test_dsl_import.py -k 'init_file or child_output or hierarchical'
PYTHONPATH=. pytest -q rtlgen/tests/test_cosim.py -k 'cosim'
```

When debugging:

1. if Python/executable and emitted RTL disagree on ROM behavior, inspect
   `init_data` / `init_file` first
2. if signed math disagrees, inspect missing `.as_sint()` / `.as_uint()` and
   missing `RoundShiftRight(...)`
3. if hierarchy breaks, inspect whether parent-visible stage wires or storage
   were accidentally left as host-local temporaries

Useful first split:

1. Python fails before compiled C++:
   start from DSL authoring, signed intent, or storage/hierarchy contract
2. Python passes but compiled C++ fails:
   start from backend codegen or signed width interpretation drift
3. Python and compiled pass but emitted RTL smoke fails:
   start from emitter/backend contract, naming, or tool-subset expectations

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
