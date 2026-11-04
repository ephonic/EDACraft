# Runtime testbench I/O

Same-source VCS fixtures cover `$test$plusargs`, `$value$plusargs`, `$sformatf`, `$sformat`, packed `%s/%0s` and `%c`. `scenarios.json` records the ordered runtime argv; `expected.json` contains complete TRACE outputs. `variants.json` adds absent, malformed, empty and overflow argv sets for `args.sv`.

The regression checks complete ordered/settled VCD streams across serial, time-wheel and threaded generators; plain executables; two actual partitions; rejected prediction replay including final output; ordinary write/coercion paths; eight compile-time and six runtime rejections; interleaved wave options and plusargs; unknown native option rejection. `numeric.sv` distinguishes two-state native integral targets from four-state integer/vector targets on malformed values. VCS omits the unpacked memory from `$dumpvars`; its four values are independently observed in stdout and native replay, while the VCS comparison explicitly records the 128 omitted memory bits.

Supported conversions and remaining format limitations are documented in [testbench-io](../../docs/testbench-io.md). Run:

```
python3 tests/testbench_io/regression.py build/dsim /tmp/testbench-io build/CMakeCache.txt
```
