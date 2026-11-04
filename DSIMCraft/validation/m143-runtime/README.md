# M143: scalar NBA enqueue ABI

The scalar `assign_nba(int,V)` adapter is kept inline for GCC/Clang. Its body still calls the same `assign_nba_planes` queue implementation, including Reactive/Re-NBA routing, vector growth, ownership and insertion order. Full-value, wide and string fallbacks remain unchanged. `DSIM_REFERENCE_NBA_INLINE` restores the previous compiler decision for an exact control. No model name, test data, process ordering or instruction budget is used to select this optimization.

Implementation: `76b46b50f14fc5f9fe6339d59eccc2d143647d50`. All 1794 packaged source members match that Git commit; source archive SHA256 `073c1e73993f612fec00208afaca633da1cb6538703c7e7e3858e5b7ffd66850`.

## Current hotspot evidence

The unchanged M142 CPU ELF was sampled with ITIMER_PROF (9106 exclusive instruction-pointer samples). `run_to` accounts for 18.69%, generic scalar publication for 15.15%, prepared publication for 8.52%, and the old `assign_nba(int,V)` call for 2.70%. These are diagnostic sample shares, not PMU counters, call-stack attribution or speedups. The owned executable and raw PCs/maps are retained in external evidence. Owned disassembly shows a stack-based V load and a large vector growth branch in the outlined old adapter.

## Development screening

Original full workloads, CPU25, Intel 2026.1.1, O2/strict/xHost/pthread; warmup then three rotated rounds. Each result is checked against the unchanged expected PERF output. CPU user+system median seconds:

| Workload | M142 | Inline | O3+IPO | Inline + O3+IPO |
|---|---:|---:|---:|---:|
| CPU | 9.11 | 8.94 | 8.74 | 8.64 |
| CRC | 3.44 | 3.42 | 3.26 | 3.26 |
| muldiv | 8.01 | 7.52 | 7.51 | 7.68 |
| AXI4 | 0.19 | 0.19 | 0.17 | 0.16 |

Only the inline adapter is selected. CPU text size falls from 278273 to 273593 bytes. O3/IPO has cross-workload benefits but is not made the default: the earlier M139 large expanded TB exceeded its unchanged compilation budget with that policy, and interactions are not uniformly beneficial. No new default compiler flags or floating-point relaxation are introduced. A separately outlined planes helper is also screened; it is not added to production.

## Acceptance

The frozen candidate passed both platforms' RTL/format parser and native Liberty DB checks, plus four affected groups: NBA storage, budget resume, interface subroutines and compiler options. Each platform has 56 NBA captures, 668 budget comparisons, 8 prediction checks and real two-partition execution; 552 ordered budget resumes and 164 checkpoint resumes; 35 interface captures, 7 commits, 7 rollbacks, 2 restores and 21 rejected cases. Eight runtime kernels passed on each platform; the Mac eight also passed ASan/UBSan. This is targeted acceptance, not a full language-conformance run.

The untimed CPU prefix matches the exact old adapter control: 5767258 steps, state hash 1604582946171822610, 921690 publications with ordered timestamp/step/ID/A/B hash 17456498821793891831, and 957631 ready pushes/pops. No scheduling work is removed.

Final native models were rebuilt through the frozen release compiler. All original workload input SHA256 values and the M142/VCS binary identities are checked. Apart from the runtime text and frozen source-root spelling, generated code matches M142 exactly. Intel O2/strict/xHost/pthread, CPU25, warmup then three rotated rounds; all 48 runs matched the expected full-workload output. The server was shared with validation on other cores, without exclusive-machine control. User+system CPU seconds exclude wall-clock license waits from speedup claims; all raw wall times remain available.

| Workload | M142 | M143 | Reduction | VCS | M143/VCS |
|---|---:|---:|---:|---:|---:|
| cpu | 9.11 | 8.86 | 2.7% | 5.70 | 1.55 |
| crc | 3.52 | 3.45 | 2.0% | 3.91 | 0.88 |
| muldiv | 8.04 | 7.57 | 5.8% | 6.92 | 1.09 |
| axi4 | 0.19 | 0.19 | 0.0% | 0.61 | 0.31 |

CPU and CRC gains are small; this does not close the process-level scheduling gap. AXI4 is short and sampled at 0.01-second time resolution; no AXI4 improvement is claimed. The larger VCS CPU sample (6.25 seconds) and the AXI4 candidate sample (0.24 seconds) are retained; no samples are filtered.

Both stable releases are active and actual entries recompiled/ran the interface fixture, matching accepted generated C++, stdout and the complete ordered waveform:

- mac: `/Users/yangfan/vibe-coding/dsim-test/releases/20261028T114022259895Z-29dac288a9a3`, SHA256 `c3a49de995d0feef2aa224faa97310cf22c5a99020d5cab9341279382b61abce`.
- linux: `/apps/EDAs/own/dsim/releases/20261028T114027Z-76b46b5`, SHA256 `a5e0d249374e34aa2e303812d25c513f99d22e348def426d5eacce851e5e9455`.

Linux defaults remain Intel O2/strict/xHost; the measurement adds the same explicit pthread flag used by the frozen baseline. There is no Mac performance claim. `source-proof.json`, release/activation receipts, `measurement.json`, `prefix.json`, kernel/group receipts, and `audit.py` bind the result to the source and actual installed binaries.

Owned raw code, native binaries, logs, waveforms and sample PCs/maps are outside Git, mirrored under `~/vibe-coding/dsim-test/evidence/m143-runtime` and `/apps/EDAs/own/dsim/evidence/m143-runtime`. `evidence-index.json` binds the two archives and per-member manifests by byte size and SHA256; `mirror-proof.json` verifies both copies. No vendor-generated code or vendor binary is archived or committed. The sampler, benchmark and publication helpers are retained here to reproduce the procedure.
