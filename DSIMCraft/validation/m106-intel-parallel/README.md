# M106 Intel compiler and independent-partition optimization

Fixed M105 generated C++ and original full CPU/CRC/muldiv/AXI4 workloads are used for compiler comparisons. `compiler-screen.py` checks five configurations; `compiler-measure.py` repeats GCC O2, GCC O3/native, and Intel O3/xHost/IPO with strict floating-point semantics. One warmup and three rotated rounds, CPU 0, unchanged checksums, separate CPU and elapsed times. Screening samples are not final performance claims.

`partition-audit.json` records the actual whole-program partition plans of all five original perf-kit inputs at 2/4/8 requested workers. They all select one execution partition. Independent arithmetic lanes are a separate scalability experiment, not evidence of parallel acceleration of the original shared-clock workloads. The source is `tests/parallel_arithmetic/lanes.sv`; the final performance run defines 400 epochs and 1000000 inner iterations (1.6 billion total iterations); the earlier 100000-inner-iteration short screen is retained separately, with no $display/$finish to couple the lanes. Instrumentation reads every logical signal after natural completion. Old and new serial C++ are byte-identical. Full-count outputs must also match immutable M105 serial and parallel execution. Only M106 1/2/4-worker timings receive one warmup and three rotated rounds; previous M105 parallel is a one-run correctness screen.

The implementation installs the resolved observer only when a positive-delay output channel is connected. This preserves the native-loop guard for independent partitions, while source partitions continue to use the observable path. Topology, message ordering, finish/exception fences, checkpoints and waveform rules are unchanged. `development-checks.json` records the affected kernel tests, the independent Python state oracle, complete VCD comparisons, X fallback, existing precise event-budget/replay tests, and ASan/UBSan on a kernel and actual generated parallel program.

The default compiler stays system C++ O2. `--cxx-flag` passes literal, repeatable argv entries; tests check spaces/metacharacters, actual optimized compilation, defaults and preservation of an existing executable after compiler failure. See [options](../../docs/compiler-options.md). MKL is installed on 103, but the integer/event hot paths do not expose a suitable BLAS/FFT/vector-math call; no unused MKL dependency is added or counted as acceleration.

## Full original workload compiler results

mn02 Xeon Platinum 8358, CPU 0; one warmup and three rotated samples. Medians in seconds, compile excluded; all 48 full timed/warmup executions have byte-identical DSIM stdout. GCC 11.5.0; Intel oneAPI C++ 2026.1.1. Explicit Intel configuration: `-O3 -xHost -ipo -fp-model=strict`. All configs use C++17/pthread. Same frozen M105 C++ for all variants; no workload count reduction. `compiler-measurement.json` retains every sample and binary/code hashes; `compiler-screen.json` retains the separate five-configuration one-run screen.

| Workload | GCC O2 CPU / wall | GCC O3/native CPU / wall | Intel O3/IPO CPU / wall |
|---|---:|---:|---:|
| CPU | 21.20 / 21.36 | 20.99 / 21.17 | 19.61 / 19.68 |
| CRC | 6.86 / 6.89 | 8.62 / 8.65 | 6.94 / 6.96 |
| muldiv | 13.74 / 13.79 | 14.37 / 14.47 | 13.25 / 13.34 |
| AXI4 | 0.28 / 0.29 | 0.31 / 0.32 | 0.27 / 0.27 |

Intel CPU time improves CPU by 7.5% and muldiv by 3.6%, but CRC costs 1.2% more. GCC O3/native increases CRC CPU time by 25.7%. The very short AXI4 run is sensitive to startup and timer resolution. These results support an optional toolchain choice, not a universal compiler switch or a claim that the VCS performance gap has closed. VCS figures from M105 are not reused as if they were concurrent M106 measurements. Shared-server variation remains visible in the retained samples.

## Independent arithmetic domains

The final test runs 1.6 billion total iterations (400 epochs x 1000000 iterations x four lanes), GCC O2/pthread, affinity CPU 0–3 on the same socket and distinct physical cores. One warmup and three rotated rounds; source, actual generated C++ and executable hashes are in `parallel-measurement.json`. Every logical signal matches the full-count immutable M105 serial and parallel references. Small-count independent Python oracle and all-signal X/known VCD regressions additionally cover the same source.

| M106 execution | CPU seconds | Wall seconds | Wall speedup |
|---|---:|---:|---:|
| Serial | 3.53 | 3.55 | 1.00x |
| Two workers / two partitions | 3.55 | 1.80 | 1.97x |
| Four workers / four partitions | 3.84 | 1.66 | 2.14x |

Four workers do not yield fourfold scaling in this shared-server test. The measurements include synchronization and scheduling overhead; no isolated cause for the remaining scaling loss is claimed. The earlier 160-million-iteration screen (about 0.36s serial) remains in `parallel-screen-short.json`; it is superseded by this longer final experiment rather than selected for a better ratio. Old M105 parallel is only a correctness screen and is not presented as a repeated speedup result.

This improvement applies to independent domains. The original five perf-kit workloads still have one executable partition, so these figures must not be substituted for CPU/CRC/muldiv/AXI4/cache thread speedups. Positive-delay channel sources retain the observer and their guarded scalar-loop fallback.

## Intel frontend and stable publication

`intel-validation.json`: the complete frontend also builds with icpx. Eleven identical generated C++ programs and eleven identical elaboration reports match the GCC frontend, covering six integer-loop models plus the five original perf-kit models. Six real simulations compiled through installed `--cxx icpx --cxx-flag ...` match their known results; ordered and settled all-signal VCD streams match GCC for the independent four-partition model. The optional Intel frontend build remains an experiment; stable frontend binaries keep the existing platform compiler.

Both stable entries are active, each with parser/format/native-DB checks and five affected regression groups. Linux additionally reruns all seven affected parallel kernels. The actual installed entries regenerate the unchanged M105 C++ for all four original complete benchmarks, compile and execute them with the original counts and checksums, and regenerate all three final parallel measurement programs with exact matching hashes. The actual release-generated four-partition program also matches the ASan/UBSan-tested C++ byte-for-byte.

- macOS: `~/vibe-coding/dsim-test/bin/dsim`; release `20261025T182239476272Z-11cb546889d6`; binary SHA-256 `bc04cad17509ba326294d3857629d71a77051464207278985005b3c8cb10ec60`.
- 103: `/apps/EDAs/own/dsim/bin/dsim` and `/apps/EDAs/own/dsim/dsim`; release `20261025T182757Z-a5d097e`; binary SHA-256 `40d46cd9174197dcdc1d2a30b23e1fbb829547d32907c5e186b91f5d12b0a760`.

Source commit `a5d097ea289eae4a7384884256375f1ed35e6de6`: all 1639 packaged files match Git, all 661 local publisher inputs match that source package, and eight runtime headers match each installed snapshot. Untracked user experiments are excluded. Cross-platform comparison: 110 C++ programs, 58 complete VCD files, 679 runtime stdout files and five result JSON files are byte-identical. Original integral/function regressions retain 285 precise budget comparisons plus accepted/rejected predictions.

`release-summary.json` and installed receipts record identities. All 1583 raw timing/code/check files were individually SHA-256 verified against `raw-evidence.json`; no slow sample is discarded. The source archive, raw evidence archive, Linux release evidence archive and final receipts are stored outside Git under `~/vibe-coding/dsim-test/evidence/m106-intel-parallel` locally and `/apps/EDAs/own/dsim/evidence/m106-intel-parallel` on 103. MKL discovery and hardware facts are in `environment.json`; no MKL computational routine is called by the simulator.
