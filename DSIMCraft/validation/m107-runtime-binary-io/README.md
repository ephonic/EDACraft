# M107 runtime / binary input evidence

Runtime implementation: isolated single-driver nets retain their stored driver and publish through `Sim::set` directly. Late multi-driver promotion, aliases, force/release, four-state wide values, observers and checkpoints keep their existing paths and semantics. No benchmark-specific workload reduction, kernel substitution or compiler flag change is used.

`profile.py` profiles an active bounded prefix of the original CPU/CRC/muldiv workloads with callgrind and checks exact state hashes and step counts. This is hotspot attribution, not full-workload timing. `screen.py` records the provisional candidate screen; final repeated results are produced by `prepare-perf.py` and `measure.py`. The final generated programs must differ from the frozen M106 programs only in the runtime header and must match the actual installed compiler output.

Full timings use original `tests/perf_kit` inputs, unchanged iteration counts, GCC `-std=c++17 -O2 -pthread`, CPU 0, one warmup and three rotated rounds of fixed M106, M107 and VCS W-2024.09_Full64 binaries. GNU time CPU and elapsed medians are separate; all measurement-program compilations finish before timing starts. DSIM stdout is byte-exact against the baseline; VCS checksum comparison normalizes existing hexadecimal space/zero padding only. Shared-server frequency/load can vary. The four measurements do not establish a universal simulator speed ratio; cache and unmeasured gate/SDF performance are excluded.

New feature: [$fread scope](../../docs/binary-io.md). Five same-source VCS fixtures cover packed and wide values, non-byte widths, two-state targets, ascending/descending fixed arrays and ranges, short/zero reads, pushback, address effects, packed slices and automatic/ref writes. Input bytes are unchanged. The regression requires complete ordered/settled VCD equality among serial, wheel, requested two-thread execution, rejected prediction replay and accepted prediction commit. It verifies a real two-partition model, explicit unsupported forms, and runtime failures. Kernel tests inspect pre-existing cursor/pushback/EOF across checkpoints and prediction decisions.

`verify-vcs.py` checks all TRACE lines and static numeric settled bit streams, omitting only explicitly named unpacked arrays that VCS does not dump. A specific VCS W-2024.09 VCD issue is asserted separately: the 24-bit packed destination changes to zero on a zero-byte EOF read in TRACE but VCS does not emit the VCD update; dsim does. This is recorded as a known waveform exception, not counted as equal bits. The other 833 numeric bits agree completely.

Final measurement, publication, sanitizer and source provenance receipts are saved beside this document. Raw generated C++, waves and execution logs are retained in hash-checked evidence archives outside Git.

## Full-workload results

Seconds, medians of three samples after one warmup. All 48 timed/warmup executions pass full output/checksum verification.

| Workload | M106 CPU | M107 CPU | VCS CPU | CPU time reduction | M107/VCS CPU |
|---|---:|---:|---:|---:|---:|
| bench_cpu | 21.34 | 20.03 | 5.71 | 6.1% | 3.51x |
| bench_crc | 6.88 | 6.52 | 3.88 | 5.2% | 1.68x |
| bench_muldiv | 13.79 | 12.49 | 6.86 | 9.4% | 1.82x |
| bench_axi4 | 0.29 | 0.27 | 0.56 | 6.9% | 0.48x |

| Workload | M106 wall | M107 wall | VCS wall |
|---|---:|---:|---:|
| bench_cpu | 21.41 | 20.09 | 8.52 |
| bench_crc | 6.91 | 6.54 | 6.67 |
| bench_muldiv | 13.83 | 12.53 | 9.67 |
| bench_axi4 | 0.29 | 0.27 | 2.38 |

AXI4 is a short control with substantial startup effects. Its apparent ratio is not an engine-throughput comparison. The CPU/CRC/muldiv results still leave a material VCS gap. [Batch diagnosis](batch-analysis.md) records the execution granularity limitation and bounded counter evidence, without attributing an unmeasured percentage of the remaining gap to batching.

## Stable publication and checks

Implementation/source freeze: `37ae34e6963ca18045c52c9fe3e73cee6838b2d3`. Both stable entries are active. Each installed entry regenerated, compiled and fully executed the four original workloads; all generated C++ hashes match `measurement.json`. Both copies of all eight runtime headers match the frozen source. The actual packed/automatic generated C++ tested by ASan/UBSan matches both installed releases.

- macOS: `/Users/yangfan/vibe-coding/dsim-test/bin/dsim`, release `/Users/yangfan/vibe-coding/dsim-test/releases/20261026T005804640396Z-7e15cb485172`; binary SHA-256 `a91fe749fa2d51fe334311773a79d6a68cce85a87d7566618403e2989bcbb5cb`.
- 103: `/apps/EDAs/own/dsim/bin/dsim`, release `/apps/EDAs/own/dsim/releases/20261026T005922Z-37ae34e`; binary SHA-256 `8c5e3f6689e0b250af9855c97177523fddc1f335abc3f14ea0299b5a1c7c0366`.

Each release reran binary input, scalar/wide operations, integer loops and gate-source checks, plus the three parser/native-DB checks. Seven related runtime kernels passed locally and on 103; the driver kernel covers repeated single-driver writes, late promotion, wide values, force/release, observers and deep checkpoints. The existing integer/function groups retain 285 exact budget/state comparisons. ASan/UBSan passed on the driver/binary kernels and actual packed/automatic generated programs.

Source proof verifies all 1648 packaged files against Git; all 664 local publisher inputs match that package. User experiments are excluded and untouched. Cross-platform comparison requires byte equality for 103 C++ programs, 82 complete VCD captures, 688 runtime stdout files and four regression result JSON files. Compiler-command stdout and path-dependent gate-source stdout are excluded explicitly.

Raw evidence has 1151 files, including all final timing samples, exact programs, callgrind records, VCS source/logs/waves, census counters, sanitizer logs, complete release reports and installed-entry checks. `raw-evidence.json` records the archive and member-manifest SHA-256. The source archive, raw archive, full per-member hashes and review receipts are mirrored under `~/vibe-coding/dsim-test/evidence/m107-runtime-binary-io` and `/apps/EDAs/own/dsim/evidence/m107-runtime-binary-io`. This does not imply full SystemVerilog/UVM or complete VCS compatibility.
