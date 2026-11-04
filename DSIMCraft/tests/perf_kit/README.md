# Original REPORT-PERF workloads

These SystemVerilog files are copied unchanged from `dsim-test/rtl-tests/perf-kit` on 2026-10-26. `inputs.json` records SHA-256 for every source. They use deterministic xorshift32 stimulus and end-to-end checksums; the measured workload counts are not reduced. CPU, CRC and muldiv are the reported slow workloads; AXI4 is the non-regression control. Cache is retained as input evidence but excluded from timing ratios because the report describes inconsistent VCS completion; the cause is unproven.

Measurement tools and raw-data location: `validation/m105-runtime/`. Compile once, pin all three binaries to the same CPU, warm up, then rotate baseline/candidate/VCS for three rounds. Report CPU and wall medians independently. Compilation, callgrind prefixes and screening are not included in final simulation times.
