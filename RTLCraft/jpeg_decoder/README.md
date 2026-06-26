# JPEG Decoder Worked Example

This directory is the main signed-datapath worked example for the current
`rtlgen` stack.

Use it when you want one realistic design that exercises:

1. signed fixed-point arithmetic
2. ROM/LUT-backed MAC structure
3. transpose and reorder storage
4. hierarchical stage composition
5. Python, compiled C++, and emitted-RTL closure

## What Lives Here

The implementation is in
[dsl_modules.py](./dsl_modules.py).

The main modules are:

1. `JpegIdct8x8`: signed row/column iDCT with ROM-backed coefficients and a transpose buffer
2. `JpegDequantZigzag`: dequant + zig-zag reorder stage
3. `JpegDecoder`: top-level token-to-pixel composition

## Recommended Rerun Order

For most JPEG-side changes, use this order:

```bash
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_idct_basic.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_cpp_idct.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_dequant_idct.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_cpp_entropy_dequant.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_verilog.py
```

What each step tells you:

1. `test_idct_basic.py`: quick Python-level executable sanity for the narrowest datapath
2. `test_cpp_idct.py`: whether Python and compiled simulator still agree on signed iDCT behavior
3. `test_dequant_idct.py`: whether stage composition and parent-owned handoff wiring are still correct
4. `test_cpp_entropy_dequant.py`: whether the longer entropy/dequant path still agrees across Python and compiled sim
5. `test_verilog.py`: `iverilog -g2012` compile smoke for the emitted SystemVerilog subset

For verbose matrix dumps while debugging, the same files still support direct
script execution, for example:

```bash
PYTHONPATH=. python jpeg_decoder/tests/test_cpp_idct.py
PYTHONPATH=. python jpeg_decoder/tests/test_dequant_idct.py
```

## How To Triage Failures

Use this split first:

1. Python fails first:
   likely a DSL authoring, signed arithmetic, storage contract, or hierarchy issue
2. Python passes but compiled C++ fails:
   likely backend codegen or signed-width interpretation drift
3. Python and compiled pass but emitted RTL smoke fails:
   likely emitter/backend contract, reserved-word naming, or tool-subset issue

More specific clues:

1. wrong negative/intermediate math:
   inspect `.as_sint()`, `.as_uint()`, `RoundShiftRight(...)`, and clip/select boundaries
2. wrong ROM/LUT behavior:
   inspect `Memory(..., init_data=...)`, `init_file`, and address-generation wires
3. wrong transpose/reorder behavior:
   inspect module-owned `Array(...)` / `Memory(...)` objects and visible read/write indices
4. hierarchy/handshake breakage:
   inspect whether stage boundaries are still connected through parent-owned wires rather than host-local temporaries

## Backend Policy

For this JPEG path today:

1. Python and compiled simulators are the primary functional closure loop
2. `iverilog` is a local compile-smoke check, not the strongest emitted-RTL oracle
3. for stronger emitted-RTL closure, prefer `verilator`, then `vcs` when available

For the mixed DSL + external Verilog + ROM-init packaging story, see
[../rtlgen/MIXED_DESIGN_COSIM_GUIDE.md](../rtlgen/MIXED_DESIGN_COSIM_GUIDE.md).

## Where The Patterns Are Documented

The JPEG-specific design patterns are summarized in
[../rtlgen/JPEG_DATAPATH_COOKBOOK.md](../rtlgen/JPEG_DATAPATH_COOKBOOK.md).

Use that cookbook for:

1. signed fixed-point authoring rules
2. LUT/ROM-backed MAC guidance
3. transpose/reorder storage rules
4. hierarchy and packaging patterns
