# Packed variable selects and timing optimization candidates

Production changes are in `src/rtl_compiler.cpp` and `include/dsim/runtime.hpp`.
The RTL and gate parsers remain separate; neither parser was changed.

- Runtime bit and fixed-width indexed part selects support four states, wide
  data, nonzero declaration bases, clipping, procedural/concatenation targets,
  module input expressions, delayed NBA target capture, blocking intra-delay
  target evaluation and rollback. Ordinary variable-width ranges are rejected.
  See [language boundary](../../docs/indexed-selects.md).
- Timing-check observers now use signal-indexed lookup and sparse callback
  groups, preserving observer registration order and checkpoint-owned state.
- Stable 4/8-way timer heaps are optional generated-C++ compile configurations.
  **Binary remains the default.** The eight-way default was withdrawn after the
  reverse-order measurement failed to reproduce the first-round gain.

Final binary-default source package: 486 files,
`/tmp/dsim-m9-default2-final.tar.gz`, SHA256
`59aab727ffdf20978b9d9671d09fa045b3ee64883559d632d146a78bd0bdb345`.
The preceding eight-way acceptance package has SHA256
`462b04fecb022c0e33d60079d1d4bec6791d4799bc788e35b7121ec96ac829fe`.
The runtime differs only in the default macro/comment; the final parallel test
also waits one tick before sampling its continuously assigned input, avoiding
an Active-region scheduling-sensitive read. Compiler C++ sources are identical.

## Verification

Local: 30 affected CTests passed with binary-default observer dispatch, including
12 heap configuration kernels. Final module input adaptation and binary-default
canonical `build/dsim` passed 50 waveform captures, seven explicit diagnostic
rejections and two rejected-prediction replay models. Captures compare every
signal's ordered history across serial, time-wheel, two-thread, VCD/DWF and
replay variants. The independent-domain case uses two real partitions.

Four macOS ASan/UBSan executions passed: two actual generated select models,
sparse/multiple timing observers, and a randomized timer FIFO/checkpoint oracle.
These are not Linux sanitizer runs or a full 128-test CTest run.

The initial `q[index:0]` rejection test exposed a real lowering bug; it was fixed
before the successful batches. Original failure is retained. Initial actual VCS
probes confirmed NBA/blocking-delay sampling and overlap order. A nonzero high
word in a 128-bit index produced a VCS difference; `vendor-probes` preserves it,
and `large_index.sv` tests dsim's explicit full-value behavior separately.
Common-range VCS comparison and final Linux acceptance are recorded below when
complete.

## Full SDF performance

Original 300,909-cell design, original full SDF, 128 outputs, CPU 0, GCC/O2,
no waveform, default nonnegative checks; no jobs, wheel or path dictionary.
These are short screenings on a shared host without warmup or locked frequency.
Every run checked all 128 outputs. Raw commands, stdout/stderr and `/usr/bin/time`
metrics are in `heap/` and `dispatch/`; `collect.py` recomputes CPU/RSS and traces.

First arity screening: old M8 default / new binary control / four-way /
eight-way / VCS CPU = 72.40 / 74.77 / 70.45 / 69.91 / 9.24 seconds.
This is a separate campaign from the following reverse-order screening.

| Configuration | Round 0 CPU s | Round 1 CPU s | Two-sample median s |
|---|---:|---:|---:|
| Binary control, old observer lookup | 71.59 | 68.51 | 70.05 |
| Eight-way, old observer lookup | 70.26 | 68.44 | 69.35 |
| Binary + direct observer lookup (final default) | 69.28 | 69.55 | 69.415 |
| Eight-way + direct observer lookup | 67.23 | 69.95 | 68.59 |
| VCS | 8.57 | 9.54 | 9.055 |

Round 1 reverses the entire order. Combined eight-way candidate improves 6.09%
in round 0 but regresses 2.10% in round 1; its median difference is only 2.08%.
It is **not adopted by default**. Direct observer lookup's median difference is
0.91%, also insufficient to claim a stable overall speedup. The final binary
configuration is about 7.67 times this campaign's VCS CPU. Do not compare this
ratio with M8's different-campaign 6.49 ratio as a code regression or improvement.
The binary control uses the same model with the unified timer API; it is distinct
from the true M8 old binary measured in the first campaign.

This turn does not claim to close the main performance gap. The next substantial
speed work remains reducing SDF intermediate events and per-cell scheduling,
with timing, checks, FIFO/delta behavior and visible waves preserved.


The preceding Linux candidate batch passed all 22 selected CTests, then failed
its VCS parallel fixture comparison. That fixture immediately read a continuous
wire after changing its select index in the same Active process. The original
source, VCS wave and failure remain in the remote `acceptance/parallel` evidence.
The final fixture waits one tick before sampling; this is a test stimulus change,
not a production fix or a claim of global same-delta VCS equivalence. Final
binary-default acceptance uses three fresh generated-model flows and new VCS
execution for the changed fixture. The original batch exit remains **1**.


## Final acceptance (2026-10-19)

`/tmp/dsim-m9-final-drGtWd` final binary-default continuation exited **0**;
its preceding eight-way batch retains exit **1**, including the original
scheduling-sensitive fixture mismatch. The final source manifest (486 files)
matches the workspace, independently checked after collection.

Three final Linux flows passed: indexed selects (50 captures, seven diagnostic
rejections, two replay models), timing-check designs, and ordinary RTL regression.
Actual VCS design/narrow/settled-parallel comparisons pass **328 + 40 + 190 = 558**
physical bit histories, locally recomputed from downloaded waves. The changed
parallel fixture was freshly built/executed by VCS; unchanged fixtures retain
source-identical actual VCS reference runs. Final native models use binary heaps.

The final compiler regenerated the complete original SDF model. Entire model
text equals the measured `dispatch2` candidate after substituting the runtime
and removing the redundant explicit arity define. Entire GCC `-E -P` outputs
are byte-identical (109,285,690 bytes each; SHA256 in
`linux/acceptance-default2/model-identities.json`). Thus the final full-model
execution evidence reuses the two actual measured `dispatch2` runs, each with
128 correct outputs. This is **not** a newly compiled full-model execution.
No full CTest-suite or Linux sanitizer claim is made.

Raw evidence is in `linux/`, summary in `linux-results.json`; `collect_linux.py`
checks terminal status, all 558 vendor bit histories and the final workspace
manifest. Canonical local `build/dsim` was rebuilt and its final binary-default,
race-free select regression passed. Source changes after the initial sanitizer
batch only select the default heap and settle the parallel test stimulus;
sanitizer executions explicitly selected arity 8.
