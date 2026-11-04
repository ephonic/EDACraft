# M114 scalar NBA storage

Implementation is frozen at `01d13b205a253541f228af1b607ea1f25d4630aa`.
Whole-variable scalar NBA records use 32 bytes instead of 56, with bit-plane
arguments on enqueue. Designs with selected/dynamic/event NBA targets retain the
original storage, as do wide, text and gate models. A selected-write microbenchmark
exposed allocation overhead, so that path was excluded before final acceptance.
This change preserves the number of NBA records and process activations.

## Full original workload measurement

GCC 11.5, `-std=c++17 -O2 -pthread`, CPU 0, one warmup and three rotated rounds
of frozen M111 / M114 / frozen VCS. All compilations finish before timings.
Inputs and complete workloads are unchanged; all 48 complete outputs pass.
Shared host and uncontrolled frequency limit precision. CPU means user+system.

| Workload | M111 CPU / wall s | M114 CPU / wall s | VCS CPU / wall s | CPU reduction | M114/VCS CPU |
| --- | ---: | ---: | ---: | ---: | ---: |
| CPU | 14.89 / 14.99 | 14.66 / 14.71 | 5.69 / 8.50 | 1.5% | 2.58 |
| CRC | 4.37 / 4.39 | 4.37 / 4.39 | 3.90 / 6.67 | 0% | 1.12 |
| muldiv | 10.98 / 11.02 | 10.22 / 10.26 | 6.90 / 9.67 | 6.9% | 1.48 |
| AXI4 | 0.24 / 0.25 | 0.24 / 0.24 | 0.57 / 2.38 | 0% | short control |

`measurement.json` contains every sample; `audit.json` independently checks all
48 raw time/output logs, identities, medians and ratios. Each reference-mode
`.text` equals frozen M111; AXI4 candidate `.text` also equals M111. Generated
model bodies remain identical. The early `screen-mixed-generator.json` accidentally
used a previous generator candidate and is rejected as isolated evidence. The
intermediate isolated screen also predates final legacy-path code restoration;
only the final full measurement above supports adoption.

Watch bitmap, short-process PC and copy-process budget candidates were withdrawn
after complete-workload screens. Their patches and results are in sibling
`m114-watch-filter`, `m114-linear-process` and `m114-copy-process` directories.

## Correctness and installation

`development.json`: 48 complete waveform captures, 668 exact budget/state checks,
eight prediction outcomes, and a genuine two-partition quiet model. A printing
fixture correctly falls back to serial; the initial test incorrectly expected
two partitions and was corrected before acceptance. `affected-mac.json` records
six additional passing groups: event/dynamic NBA, assertions, gate source and
REPORT5/6. `sanitizers.json`: three kernels and two generated models pass
ASan/UBSan. `vcs.json`: four same-source models, 37 TRACE lines and 627 static
numeric bit timelines agree. The stores probe settles its forced net for 1ns
before release in both tools to avoid an Active-region race; the original source
is still covered against the legacy dsim backend.

Both stable entries have been updated. Mac release
`20261026T110648551297Z-7ef1b584d68f` passes parser/format/native-DB checks plus
NBA/gate/REPORT6. Linux release `20261026T105847Z-01d13b2` passes parser/format/
native-DB, NBA/event-NBA/gate checks and runtime kernels. `installed-*.json`
verify eight runtime headers per platform, then regenerate and fully execute
all four original benchmarks through the actual installed entry; C++ hashes
match measured inputs. `release-*.json` and `source-proof.json` identify the
binary, immutable runtime and 1,674-file source archive.

`raw-*.json` identify member-verified private archives of 6,569 Mac and 431 Linux
files. Logs, generated dsim C++, full waves and measurement text sections are
preserved under both installations' `evidence/m114-nba-storage/` directories;
executables, proprietary vendor-generated code and user experiments are excluded.

The modest NBA storage gain does not explain VCS's main advantage. The subsequent
[VCS-side investigation](../m115-vcs-mechanisms/README.md) changes the focus to
static grouped commits and compiled successor propagation.
