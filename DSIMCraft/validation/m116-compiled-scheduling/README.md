# M116 compiled scheduling experiments

The baseline is frozen M114. All screens use unchanged complete CPU/CRC/muldiv
workloads on server 103, CPU 0, GCC 11.5, `-std=c++17 -O2 -pthread`.
These screens have two rotated rounds, no warmup, and variable shared-host load;
they select experiments, not final speed claims. Complete stdout matches the
original baseline in every successful screen. Disabling each candidate reproduces
the frozen M114 `.text` bytes for all three programs.

Candidate/reference CPU median ratios (lower is faster):

| Screen | CPU | CRC | muldiv |
| --- | ---: | ---: | ---: |
| staged | 1.015 | 0.937 | 1.023 |
| loop-commit | 1.007 | 1.016 | 1.011 |
| callback | 0.955 | 0.998 | 1.079 |
| notify | 1.284 | 1.189 | 1.001 |
| notify2 | 1.142 | 1.056 | 0.979 |
| wait | 0.933 | 1.014 | 0.998 |

`staged` writes pending slots per statement; `loop-commit` fuses pure consecutive
NBA statements and uses a generic grouped commit; `callback` unrolls that commit.
The last screen also has a `block_only` control that fuses statement execution
but retains per-assignment records. CPU/CRC/muldiv coverage is respectively
9/2/10 syntactic groups with 39/6/44 pending scalar slots; AXI4 falls back because
it needs partial NBA destinations. Grouping does not remove ordinary `set`
updates, notifications, or all per-process scheduling work. The candidates show
no consistent overall benefit and were withdrawn from production. Archived
patches apply to commit a22ced5; `staged-kernel.cpp` covers the staging API's FIFO,
reentry, deep snapshots and partial prefixes. The fused `try` budget path was
screened on full outputs but did not complete release acceptance.

`notify` generates a callback for every known ordinary source, using a separate
callback table. `notify2` limits callbacks to sources with at least two registered
wait entries and stores the pointer on Signal itself. Both retain original watch
registration order and ordinary enqueue/region rules. Both regress CPU and/or
CRC and were withdrawn. The all-source implementation and valid high-fanout
implementation are in `all-notify-candidate.patch` and `high-fanout-only.patch`;
the former also contains the disabled NBA prototype. The archived `notify-tests`
are intended to be restored to `tests/compiled_notify` with the matching patch.
They passed FIFO/edge/invalidation/checkpoint kernels, ten complete VCD captures,
262 exact budget/state comparisons and prediction acceptance/rejection. Removing
runtime interpretation by adding another indirect callback is insufficient here;
these measurements do not justify directly executing combinational processes
inside half-committed NBA batches.

The retained experimental implementation is compiled **wait binding**. Each eligible ordinary wait
site carries its bound process ID into generated C++. Same-site rearm directly
checks Process.last_wait_site and sets waiting; first entry and site switches
still call the original arm_wait. This avoids the generic WaitSite lookup on a
hot path without changing event counts, queue order, logical steps or snapshots.
Structured signal/edge references are retained on WaitIR, independently of its
emitted C++ representation. Complex events, named events, dynamic process/fork
control, gate/wide/string models and requested parallel lowering retain generic
arming. `DSIM_REFERENCE_COMPILED_WAIT=1` provides the original path; disabling
wait-rearm caching also disables this candidate.

The warmed three-round full-workload retest does **not** confirm the screening
improvement. CPU/CRC/muldiv CPU medians are 16.15/4.69/10.85 s versus M114's
15.87/4.60/10.70 s (1.8%/2.0%/1.4% slower). Wall times show substantial host
preemption, and CPU frequency is uncontrolled; this is insufficient evidence
for adoption. Stable installations remain on M114.

The production compiler keeps this path **off by default**. To exercise it use
`--cxx-flag -DDSIM_EXPERIMENTAL_COMPILED_WAIT=1`. A separate explicit reference
macro and the existing disabled-rearm-cache control retain generic arming.
`tests/compiled_wait` and the publisher's `compiled_wait` check group exercise
this optional path. The warmed experiment used a provisional default-enabled
source; the final opt-in version must reproduce its experimental `.text` when
enabled and M114's `.text` when disabled. This is a narrowly scoped experiment,
not completion of P0 grouped commits, P1 direct propagation or P2 region fusion.


Final warmed full-workload medians (CPU / wall seconds):

| Workload | M114 | Experimental binding | Frozen VCS |
| --- | ---: | ---: | ---: |
| bench_cpu | 15.87 / 16.28 | 16.15 / 35.01 | 6.27 / 9.29 |
| bench_crc | 4.60 / 4.62 | 4.69 / 4.71 | 4.54 / 7.35 |
| bench_muldiv | 10.70 / 10.76 | 10.85 / 11.64 | 8.87 / 12.55 |
| bench_axi4 | 0.32 / 0.92 | 0.35 / 0.69 | 0.82 / 4.67 |

These are this session's observations, not a revised VCS speed claim. VCS
startup and host preemption affect wall time; CPU frequency is uncontrolled.
The very short AXI4 case remains a correctness/control workload. `audit.json`
independently verifies all 48 raw logs/outputs, medians, binary identities and
nine original RTL/TB/include source hashes. No original workload was shortened
or changed for timing.

The separate 200000000-tick Callgrind prefixes retain identical executed steps
and complete signal-state hashes:

| Prefix | M114 instructions | Binding instructions | Reduction |
| --- | ---: | ---: | ---: |
| bench_cpu | 429224803 | 415884666 | 3.11% |
| bench_crc | 82225673 | 81276508 | 1.15% |
| bench_muldiv | 91581039 | 90080273 | 1.64% |

The reduced instruction counts do not establish whole-workload runtime gains.
No branch/cache mechanism is claimed as the established cause of the remaining
runtime difference. `default-proof.json` verifies final default `.text` equals
M114 and opt-in `.text` equals the measured prototype for all four workloads;
eight additional complete executions match the baseline output. The proof uses
the production opt-in guard rather than the provisional default-enabled guard.

`development.json` records the optional-path regression, NBA storage, conditional
events, concurrent assertions, event NBA and ASan/UBSan checks. The native,
reference, uncached and time-wheel kernel variants pass. Scope does not imply
all VCS features are supported. `stable-unchanged.json` checks both installed
M114 binary identities; no candidate release has been activated.

Member-verified private archives retain generated dsim source, full waves,
budget logs, timing logs, profiles and text sections. `raw-mac.json`,
`raw-linux.json` and `evidence-mirror.json` identify their hashes and copies under
both installations' `evidence/m116-compiled-scheduling/` directories. Executables,
vendor-generated proprietary source and user experiments are excluded.
