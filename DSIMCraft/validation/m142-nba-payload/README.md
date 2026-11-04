# M142: scalar NBA publication ABI

The generic whole-variable NBA commit now sends the stored A/B planes directly to `set_planes`. The previous path reconstructed a 24-byte `V` and passed it through the stack-based `set(int,V)` ABI even though the callee already supported register arguments. Normalization, X/Z, two-state conversion, forces, dynamic activation mapping, change detection, observers and FIFO notification all remain in the same publication implementation. Wide/string/reference-scalar builds retain the old entry. `DSIM_REFERENCE_NBA_PLANES` restores the precise old compact-NBA call for differential checks.

This is a data-transfer optimization at an existing scheduler boundary. It does not implement combinational DAG fusion, eliminate intermediate signal notifications, merge NBA batches or claim that the structural scheduling gap to VCS is closed. There are no benchmark/module names in the runtime change.

Implementation commit and all 1794 source-member hashes are bound by `source-proof.json`. The source archive is stored with the release evidence, outside Git. User-owned `experiments/matvec16/` is excluded.

## Investigation and rejected candidates

`profile.json` samples the current M141 CPU executable, not the historical M130 executable: 9588 exclusive PC samples, with 22.07% in `run_to`, 10.23% in generic `set`, and 8.07% in prepared `set_planes<true>`. These are diagnostic shares, not removable time estimates. Inspection of owned DSIM instructions found repeated `V` construction and stack copying before the whole-NBA setter call. A debug rebuild produced a different `.text` hash, so no debug-line attribution is used for the original executable.

The initial complete four-workload screen uses Intel 2026.1.1, O2, strict floating point, xHost, pthread, CPU 25, warmup plus three rotated rounds. Compressing the common NBA payload from 32 to 24 bytes regressed CPU (9.59→9.68s) while improving muldiv (9.12→8.77s); it was rejected, avoiding new ownership machinery for mixed gains. Testing edges before loading process state also regressed CPU to 9.68s and was rejected. Their sources and logs remain in raw evidence.

A second CPU screen rejected cold budget throws (9.63s), outlining NBA commits (9.56s, negligible), direct queue emplacement (9.47s, limited gain), and O3 alone (9.62s) against 9.59s reference. O3+IPO reached 8.69s on this CPU workload, but has not passed full cross-workload/feature validation; it is not enabled by this release. A parallel development screen of the accepted plane-call candidate on CPU 27 reached 9.10s against 9.59s. Development screens are not the final release measurement.

## Semantic verification

The extended NBA storage regression compares native, old compact call, legacy full payload, time-wheel and actual two-partition executions. It checks complete ordered and settled signal streams, four-state/64-bit/partial writes, budget cuts, delayed slot reuse, checkpoints and prediction accept/reject. Scalar-reference compilation also checks the fallback guard.

Eight compact-NBA/event-NBA/typed-store kernels run under Mac ASan/UBSan and on Linux Intel, including ordinary and compact gate stores, named/expression events, time-wheel scheduling, delayed queues and rollback. The fixed CPU diagnostic prefix preserves all 921690 ordered publications (timestamp, step, signal, A and B), 5767258 execution steps, 957631 ready pushes/pops and the historical all-signal hash. This untimed prefix is not substituted for full-workload performance runs.

Five affected regression groups are NBA storage, budget resume, typed stores, interface subroutines and compiler options, plus mandatory RTL/format/native-DB parser checks. The first Mac publisher correctly rejected a test-harness change during its run. Its failure is retained. The changed NBA group is rerun against frozen source; the other four completed checks are reused only after proving every production input, runtime byte and their harnesses equals the frozen archive. `bind-mac.py` records that provenance explicitly.

## Formal runtime comparison and publication

`measure.py` rebuilds all four unchanged original workloads from the staged Intel release, proves that only the embedded runtime changed, then compares M141, M142 and the frozen VCS executable using the same Intel flags, pinned CPU 25, warmup and three rotated rounds. Every run must match the original expected output. Reported time is process user+system CPU seconds; raw wall time is retained and includes VCS startup/license waiting. No cache/VCS timing ratio or overall suite coverage percentage is inferred.


Formal median process CPU seconds (warmup excluded):

| Original workload | M141 | M142 | Reduction | VCS | M142 / VCS |
|---|---:|---:|---:|---:|---:|
| CPU | 9.60 | 9.12 | 5.0% | 5.69 | 1.60 |
| CRC | 4.77 | 3.48 | 27.0% | 3.91 | 0.89 |
| muldiv | 9.06 | 8.01 | 11.6% | 6.91 | 1.16 |
| AXI4 | 0.19 | 0.19 | 0.0% | 0.57 | 0.33 |

All 48 runs, including warmups, match the expected complete-workload outputs. Source comparison proves that only the embedded runtime changed. The two DSIM versions use Intel O2/strict/xHost/pthread with no IPO. The runner supplies `--cxx-flag -pthread` explicitly, matching the frozen baseline flags. The VCS executables match the SHA256 identities of the source-bound prior comparison; no vendor C/C++ or binaries are exported. One CPU/VCS sample was 6.45s versus 5.69/5.68s; all raw samples are retained and the median is reported. AXI4 is short and measured at 0.01s granularity; no improvement is claimed there. Ratios describe these four workloads and this server, not general DSIM/VCS performance.

Both platforms pass the five affected regression groups and eight targeted kernels; Mac kernels also pass ASan/UBSan. The source-bound Mac release is `20261028T110625561778Z-0dc5f7bf23fb`; Intel Linux is `20261028T105740Z-66a1530`. The local stable entry and both remote stable entries have been activated and each actual entry regenerates the expected model, output and complete ordered wave. `mac-binding.json` preserves the failed initial Mac publication and the exact reuse/rerun boundary. `mac-activation.json` and `linux-activation.json` bind active compiler identities.

Raw owned artifacts, native binaries, generated models, waves, logs, samples and source are stored outside Git under `evidence/m142-nba-payload` on both hosts. The final evidence index, member manifests and mirror proof bind their identities. The CPU gap remains substantial: M142 still needs about 1.60 times VCS's process CPU time here. Generic DAG fusion and further process/batch scheduling remain future work.
