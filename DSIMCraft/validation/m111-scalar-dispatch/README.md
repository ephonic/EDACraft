# M111 single-core scalar update and case dispatch

The implementation uses [scalar bit-plane arguments and constant case dispatch](../../docs/scalar-dispatch.md). The scheduler retains its existing behavior. Provisional reference-argument and Active FIFO batching experiments are recorded separately; they are not final performance samples.

The final measurement uses the unchanged complete CPU, CRC, muldiv and AXI4 workloads, frozen M110 and VCS W-2024.09_Full64 executables, GCC 11.5 `-std=c++17 -O2 -pthread`, CPU 0, one warmup and three rotated rounds. All compilations finish before timing begins. CPU and wall medians are reported separately. Shared-host frequency/load is not controlled; all samples are retained. The short AXI4 workload is not a throughput claim.

`development.json` records the new 30 complete VCD captures, 501 exact budget/state comparisons and six prediction outcomes. Fourteen affected checks pass, including kernels, qualified selections, event expressions, integral types, REPORT5/6, subroutines and existing wait/function paths. Two legacy groups initially encountered protected VCD files left in reused build directories; they were rerun successfully in fresh directories. `sanitizers.json` records three generated-code and one runtime-kernel ASan/UBSan checks. Vendor comparison exposed a pre-existing side-effecting comma-label short circuit, corrected before final acceptance. All four measured generated programs remain byte-identical after this correction (`final-code.json`).

| Full workload | M110 CPU / wall (s) | M111 CPU / wall (s) | VCS CPU / wall (s) | CPU reduction | M111/VCS CPU |
| --- | ---: | ---: | ---: | ---: | ---: |
| CPU | 16.77 / 16.83 | 14.89 / 14.95 | 5.72 / 8.54 | 11.2% | 2.60 |
| CRC | 5.25 / 5.27 | 4.42 / 4.44 | 3.92 / 7.69 | 15.8% | 1.13 |
| muldiv | 11.90 / 11.94 | 11.07 / 11.11 | 6.90 / 9.72 | 7.0% | 1.60 |
| AXI4 | 0.25 / 0.26 | 0.24 / 0.25 | 0.58 / 6.37 | — | — |

`measurement.json` retains every sample; `audit.json` independently verifies 48 raw time logs and complete benchmark outputs. `environment.json` checks frozen M110/VCS identities and all original source hashes, including the CPU instruction-memory include. VCS wall time includes its startup overhead. These measurements are not a general VCS compatibility or speed claim.

`profile.json` uses exactly the same 200000000-tick active prefixes. CPU instructions decrease 461207692→433928190 (5.9%), CRC 87393743→82635005 (5.4%), muldiv 95858721→93122944 (2.9%). Executed-step counts and complete signal-state hashes match. Instruction counts are separate from CPU timings. Signal update/notification and scheduler dispatch remain the principal CPU hotspots; this iteration does not close the overall VCS gap.

`vcs.json` records 33 TRACE lines and the complete settled timelines of 499 static numeric bits across three probes. The cases and wide probes use the original test sources. The stores probe changes `release bus;` to `#1;release bus;` in one common input used by both simulators: the original changes drivers and releases the forced net in the same Active slot, making its transition-counter result sensitive to process order. Both source hashes and the preparation are recorded. The original remains in the native/reference/backend regression; its counter discrepancy is retained in the raw evidence and is not counted as a VCS match. This preparation does not affect any performance workload. `label-evaluation.json` retains the old-release discrepancy and the fixed comma-label result.

Final implementation source is `12e798715da4b467bba25e6ae4badb747fa67659`. `source-proof.json` verifies all 1664 packaged files against that Git tree; user experiments are excluded. The local publisher reports a dirty tree because validation metadata and user experiments are outside its packaged inputs; the packaged source identity is checked separately. `release-mac.json` and `release-linux.json` identify the immutable releases and their eight/nine checks. The stable entries are `~/vibe-coding/dsim-test/bin/dsim`, `/apps/EDAs/own/dsim/bin/dsim` and `/apps/EDAs/own/dsim/dsim`.

`installed-mac.json` and `installed-linux.json` record recompilation and complete execution of all four unchanged workloads through the actual stable entries, including measured C++ hashes and runtime-header hashes. `cross-platform.json` records 90 generated C++ programs, 116 complete VCD captures, 2083 runtime outputs and four result JSON files with identical bytes. `release-summary.json` summarizes the final identities. `raw-evidence.json` and `evidence-mirror.json` identify the verified raw archive and its local/103 copies; these larger artifacts are retained under each installation's `evidence/m111-scalar-dispatch` directory.
