# M71: reported-case intake and fixed array declaration copies

Completed together with the subsequent [M72 frontend fixes](../m72-frontend-compat/README.md).
The external cases were examined before extending simulator functionality.

The carry archive's original failure was a compilation timeout. Rechecking the
exact RTL/testbench with the frozen M70 stable compiler took 84.89 seconds to
compile and 0.51 seconds to run. All 290 observations / 2,320 output words matched
both the archived same-source VCS output and the independent archived expected
values. See `carry-recheck.json`; this does not establish a speed improvement.

Five other archives carry explicit HARNESS-REJECTION records for data and clock
drives racing in one active region. Original inputs and logs were preserved.
Corrected testbenches drive data, wait one time unit, drive controls, then observe
three units later, retaining the original RTL, vectors, four-unit event period
and observation inventory. All 7,919 observations matched independent expectations
with both dsim and actual VCS. `corrected-dsim.json` and `corrected-vcs/` retain the
results. The race-containing originals are not counted as deterministic numerical
simulator failures. No active numerical defect was reproduced in these archives.

Six protected fixtures now live in `tests/reported_cases`, with provenance and
source fingerprints. The full final targeted regression passed; the publisher
also executes all six against each candidate stable binary before switching its
symlink. `reported-cases-native.json` records the development build results.

Fixed unpacked variable declarations now copy compatible fixed arrays/subarrays,
with static startup initialization, static sharing, automatic entry lifetimes,
declaration order, multidimensional copies and snapshot isolation. RTL declaration
grammar marks the declaration before validating array ranges. Initializer copy
buffers remain lexical C++ snapshots, with existing activation/partition/replay
machinery. See [support scope](../../docs/fixed-initializers.md).

Five shared fixed-initializer models passed 65 native waveform captures, five
failed predictions, nine rejection cases and an actual two-partition execution.
All five also passed unmodified source TRACE checks on VCS W-2024.09; source
copies and logs are in `vcs/`. This batch does not claim full VCS waveform
comparison for these five models. Four generated programs and compiler generation
paths, including cancellation and parallel storage, passed ASan/UBSan and complete
native stream comparison in [M72 sanitizer evidence](../m72-frontend-compat/sanitizers/results.json).
The repeated parser analysis/clone/cleanup test also passed with sanitizers;
leak detection was disabled. General assignment patterns, array returns, scalar
nonconstant static initialization and previously documented VCS differences remain.
