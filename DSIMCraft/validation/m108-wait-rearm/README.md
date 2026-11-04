# M108: ordinary RTL sensitivity rearm cache

A process returning to the same ordinary sensitivity list retains its subscription generations. `arm_wait` only needs to set the process's waiting flag; it avoids rewriting every input watch. The first arm and switches between sites use the original generation update. Dynamic waits, both zero/nonzero delays, static fork joins and wait fork invalidate the cache. Expression events, named events, ordered waits, process control and dynamic fork models retain the original path because they can resample values, change ownership or cancel subscriptions. `DSIM_DISABLE_WAIT_REARM_CACHE` is an internal differential-test switch.

The cache occupies existing `Process` padding: ordinary processes remain 24 bytes and watches remain 16 bytes. Snapshots own the cache along with process and watch state. Queue order, signal publication, NBA, instruction/event accounting, force, wave recording and observer code are unchanged. This removes redundant subscription writes; it does not fuse RTL processes or implement evaluation regions.

`prepare-perf.py` requires each generated program to differ from the frozen M107 program only in `runtime.hpp`. `measure.py` uses unchanged complete CPU/CRC/muldiv/AXI4 workloads, GCC 11.5 `-std=c++17 -O2 -pthread`, CPU 0, one warmup and three rotated M107/candidate/VCS rounds. All compilations finish before timing. Every DSIM output is byte-checked; VCS numeric checksums permit existing hexadecimal zero/space padding only. CPU and wall medians are reported separately. AXI4 is a short startup-heavy control. Shared-server clocks/load are not fixed, and these results are not a universal speed ratio.

`census.py` is diagnostic, excluded from timing. It executes fixed 200000000-tick prefixes and verifies the exact pre-existing step counts and four-state signal hashes. It counts actual cache hits and avoided watch-generation stores. `tests/wait_rearm` covers repeated/switching/duplicate/empty lists, dynamic waits, inactive/timer resumes, NBA, repeated checkpoints, prediction accept/reject, complete ordered/settled VCD streams, and exact exhausted-budget states versus the original rearm path. Existing expression/named/ordered/fork/event-NBA kernels protect fallback paths. Actual generated RTL and wait kernels are checked with ASan/UBSan.

Final timing, publication and source-identity receipts are stored beside this file. Generated programs, complete waves and execution logs are retained outside Git with member hashes.

## Full workload results

Seconds, medians after one warmup and three rotated rounds. All 48 full warmup/timed outputs/checksums pass. No compiler changes or overlapping compilation during timing.

| Workload | M107 CPU | M108 CPU | VCS CPU | CPU reduction | M108/VCS CPU |
|---|---:|---:|---:|---:|---:|
| CPU | 20.16 | 17.01 | 5.68 | 15.6% | 2.99x |
| CRC | 6.61 | 6.35 | 3.89 | 3.9% | 1.63x |
| muldiv | 12.51 | 11.96 | 6.83 | 4.4% | 1.75x |
| AXI4 control | 0.27 | 0.27 | 0.57 | 0.0% | 0.47x |

| Workload | M107 wall | M108 wall | VCS wall |
|---|---:|---:|---:|
| CPU | 20.22 | 17.06 | 8.47 |
| CRC | 6.63 | 6.37 | 6.69 |
| muldiv | 12.54 | 12.00 | 9.64 |
| AXI4 control | 0.28 | 0.27 | 3.38 |

Bounded diagnostic counts (not timed): CPU 1181575/1201657 cached arms avoid 6844556 watch stores; CRC 104217/104692 avoid 124218; muldiv 179266/181900 avoid 252004. Exact baseline step counts and full four-state state hashes match all three prefixes. This explains the much larger CPU benefit without claiming fewer RTL events or instruction steps.

Development: 19 related kernel tests, 52 complete VCD captures (10 wait, 6 scalar, 36 integral loops), 547 exact budget/state comparisons (262 wait +167 scalar +118 integral), prediction commit/replay and ASan/UBSan wait/fixed/static-fork kernels and actual generated RTL pass. Gate-source CLI regression passes. Publication receipts below identify the immutable releases and actual installed-program matches when completed.

## Static-fork correctness boundary and timing identity

The final cache explicitly invalidates on both static fork join and wait fork, which increment the parent's wait generation. A new test reproduces the missed subsequent wake before the fix and passes after the fix, both cached and reference paths. Final release tests include this variant. Both stable entries were kept at M107 while correcting this boundary.

The two added invalidations are inside `DSIM_FORK_JOIN_ENABLED`, absent from all four timed workloads. `prove-fork-fix.py` preserves the original measured C++ and report, requires that these are the only source differences, then requires exact preprocessed C++ equality and byte-identical rebuilt executables for every workload. `fork-fix-binary-identity.json` records both C++ hashes and the unchanged measured/final binary hash. Consequently the original 48 timing records measure the exact final executable bytes, even though the final generated C++ contains this additional inactive conditional code. `measurement.json` explicitly records both `measured_cpp_sha256` and final `cpp_sha256`; the raw archive retains both programs and the original report. Actual installed entries must still regenerate the final C++, compile and run every complete workload. No timing samples are silently replaced.

The additional final-source fork/join RTL regression passes 75 captures (existing VCD/DWF regression formats), three actual rollbacks, five explicit rejects and two real execution partitions. These captures are separate from the 52 VCD count above; no DWF work was added.

## Final stable publication

Source freeze: `2f41642f64cfa459adbb53a519123a830c7129b9`. All 1651 packaged files match this Git commit; all 667 local publisher inputs match the package. User experiments are excluded and untouched. Both stable entries passed the parser/native-DB checks, four affected regression groups and 19 related kernels (the local kernels were tested against the same frozen source; Linux kernels run in the immutable release build).

- macOS entry: `/Users/yangfan/vibe-coding/dsim-test/bin/dsim`; release `/Users/yangfan/vibe-coding/dsim-test/releases/20261026T020521177194Z-b57f6ea4b249`; binary SHA-256 `5bfd2325447e0dfe4dc9df2fcb9406a4fd600eb3c09f1e7b989692b9613e734e`.
- 103 entry: `/apps/EDAs/own/dsim/bin/dsim` (also `/apps/EDAs/own/dsim/dsim`); release `/apps/EDAs/own/dsim/releases/20261026T020504Z-2f41642`; binary SHA-256 `9383dc9ae713a5db105dd054bedfe8833ba7d9b6c03ec791b16672e9688864ba`.

Each installed entry regenerated the final measured C++ for every workload, compiled and executed all four complete workloads, verified eight immutable runtime headers, and matched the actual sanitizer-generated wait RTL input. Each release repeats 52 complete VCD captures and 547 exact budget/state comparisons. Cross-platform equality covers 77 C++ programs, 52 entire VCD files, 1179 runtime stdout files and four result JSON files. The new wait RTL agrees with VCS for all 81 numeric bits and full settled timelines on both releases. This is a tested runtime optimization, not complete VCS language support or evaluation-region fusion.

`release-summary.json` records the identities and checks. The raw evidence archive and per-member hash manifest retain 1928 files, including every timing/warmup log, original/final source and binary-identity proof, VCS input/waves, census and sanitizer inputs/logs, release reports and actual installed-entry executions. Private evidence mirrors accompany both stable installations.
