# M109 runtime optimization

See [implementation and boundaries](../../docs/runtime-windows.md). Baseline: frozen M108 (`2f41642`); VCS W-2024.09_Full64 on 10.131.254.103. Original RTL/TB files and workloads remain unchanged. The final comparison uses GCC 11.5 C++17 O2 pthread, CPU 0, a warmup and three rotated rounds with complete output checks; CPU and wall time are separate. All our remote compilation finishes before each timing run.

PC fallthrough/direct jumps and broad arithmetic-expression fusion were screened and withdrawn. Only pure complex one-bit predicates, natural parallel windows and one-copy checkpoint restore are retained. Raw provisional data is separate from final data.

The parallel component benchmark uses four independent kernels and reports synchronization count, checksum and elapsed time. Its results describe synchronization/snapshot overhead, not shared-clock RTL throughput. The restore component reuses the same checkpoint and checks the accumulated result.

The old `parallel_compiled` SDF oracle omits `TRACE t=0 z=x` already emitted by installed M108 in its serial variant. This pre-existing mismatch is recorded separately and is not counted as a passing vendor comparison. RTL integration, positive-delay kernel tests and direct before/after SDF comparisons cover the changed coordinator.

## Final original workload measurement

| Workload | M108 CPU / wall (s) | M109 CPU / wall (s) | VCS CPU / wall (s) | CPU change |
|---|---:|---:|---:|---:|
| CPU | 17.05 / 17.11 | 16.75 / 16.80 | 5.70 / 8.51 | -1.8% |
| CRC | 6.34 / 6.36 | 6.33 / 6.35 | 3.90 / 5.73 | essentially unchanged |
| muldiv | 11.97 / 12.01 | 11.77 / 11.81 | 6.99 / 9.69 | -1.7% |
| AXI4 | 0.26 / 0.27 | 0.26 / 0.27 | 0.56 / 3.37 | unchanged |

All 48 complete outputs and raw timing logs were independently audited. Current CPU/CRC/muldiv CPU time is still 2.94/1.62/1.68 times VCS. These small serial gains do not resolve the main throughput gap. AXI4 is a short startup-heavy control. Server frequency/load is uncontrolled; all three samples, including a slower VCS muldiv sample, are retained. CRC's 0.01s difference is not presented as a demonstrated speedup.

## Component measurements

Four independent kernels, pinned to CPUs 0–3, one warmup and three alternating rounds:

| Component | M108 wall (s) | M109 wall (s) | Synchronizations M108 → M109 |
|---|---:|---:|---:|
| 4 event domains, 250000 events per domain | 2.866830 | 0.022369 | 250000 → 246 |
| Same domains with earliest global finish | 3.273040 | 0.019391 | 200001 → 197 |
| 3000 restores of 10000-signal checkpoint | 0.557048 | 0.302605 | not applicable |

These measure synchronization-dominated independent kernels and snapshot restore, not VCS speed or the original shared-clock RTL. Every final checksum agrees; finish replays exactly once in both versions. Checkpoint restore elapsed time falls 45.7%; snapshot capture remains a full copy.

New regression: 44 complete VCD captures, 261 exact exhausted-budget/state comparisons, six prediction accept/reject executions, actual four-partition RTL and invalid window options. Added natural-window kernel coverage includes dense clocks, positive-delay channels, quiescence, explicit continuation and exceptions beyond finish. Eighteen affected kernels and four ASan/UBSan programs pass. Existing scalar, integral-loop, file-transaction and final/bind suites pass; the RTL-only compiler integration passes. The pre-existing SDF oracle discrepancy remains recorded, while six before/after SDF captures agree with installed M108. The new same-source VCS model agrees on 70 TRACE lines and all 573 static numeric waveform bits across their complete settled timelines.

Immutable release identities and installed-entry checks are recorded separately beside this file.
