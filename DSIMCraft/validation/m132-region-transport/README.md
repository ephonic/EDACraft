# M132: four-state conditional correction and validated fixed-width stores

The final release corrects scalar and wide conditional merging: an ambiguous selector now converts identical Z branch bits to X, matching fresh VCS. Known selectors continue to pass Z through. At the user's request, functional completion takes priority and formal runtime optimization measurements are deferred. The earlier store work is retained with differential validation; its development screens are not final-release speed claims.

M131's fresh native CPU samples assign 11.34% to scalar store entry, normalization and comparison, and another 13.05% to subscription checks/enqueues. This change specializes the first part where destination width and ownership are proven. It does not eliminate publications, watchers, ready events or logical steps.

The compiler uses the existing unique whole-net driver proof, excluding aliases, connected bits, initialization and force. Computed expressions and narrowed copies emit `set_sized<Width>`. Full-width identity copies retain the original call: expanding comparisons into their short shared leaf handler increased code/register pressure and regressed CRC during screening. Selection depends on IR expression/type facts, with no benchmark, module-name, instruction or program-content predicates. CPU/CRC/muldiv/AXI4 have 49/0/5/4 distinct eligible nets.

The call-site entry masks both four-state planes and compares them with the old value. A shared publication template preserves all original width, observer, path/property, edge decoding, stale-wait generation, armed-mask and FIFO notification behavior. The normal entry still normalizes, compares and publishes inside one call. Strings, wide vectors, force and two-/mixed-state paths keep their original implementation. Clang/Intel enable the optimized entry by default; GCC requires `DSIM_EXPERIMENTAL_TYPED_STORES`, and `DSIM_REFERENCE_TYPED_STORES` forces the old entry.

Implementation is frozen at `b9f9cfb5c327b8c64403ccfd15bcbf4d4a88387a`. All 1715 source archive members match their Git blobs. The publisher supports `--stage-only`, so reviewable immutable release builds can be checked and timed before either stable entry changes. The untracked user `experiments/matvec16` files are excluded from the package and untouched.

## Development experiments

All screens use the original complete four-workload fixtures, with compilation finished before their measurements. These are development screens, separate from the final installed comparison. Samples, including outliers, are retained. No portable Mac speedup or CPU instruction-count claim is made.

* `screen.py`: transfer an existing cohort event token between activations. No sufficiently stable overall gain.
* `snapshot-screen.py`: snapshot same-input operands once per cohort. Little overall gain.
* `ablation.py`: snapshot/rearm-mask/combined three-round ablation. Reference CPU 8.74s, snapshot 8.73s, rearm 8.65s and combined 8.68s; not enough benefit to keep this extra runtime state/API. The complete cohort candidate patch is retained and withdrawn.
* `typed-screen.py`: all eligible unique nets, split normal entry/publication helper. A reference CPU outlier made the apparent reduction misleading, and CRC regressed about 6%; withdrawn.
* `typed2-screen.py` / `typed3-screen.py`: shared template, preserving a same-call normal path. All-net expansion still regressed CRC; withdrawn. Their patches are retained.
* `region-screen.py`: restrict stores to independent cohort bodies. Correct but little/no confirmed complete-workload gain; superseded.
* `prepared-screen.py`: compare inside the prepared callee instead of its caller. Little gain; withdrawn.
* `expression-screen.py`: computed/narrowed-net rule adopted by the final source. This two-round screen only selected the candidate; it is not the final performance claim.

## Semantic coverage

The dedicated 160-transition C++ kernel covers widths 1/5/8/32/64, 0/1/X/Z edges, input bits outside destination width, identical writes, observer width, pending-checkpoint replay, stale waits and repeated NBA. Native/reference kernels also run under Mac ASan/UBSan. The SV fixture adds signed arithmetic, mixed computed outputs, X/Z, dynamic packed selection, repeated NBA, delta cycles and an observer that rewrites an input.

Nine-model differential checks cover ordered and settled waveforms, serial/wheel/parallel captures, low budgets, repeated checkpoint restore and prediction acceptance/rejection. Each platform checks 90 captures, 2367 budgets, 18 predictions and 1248 batch-kernel states. Of 648 replay comparisons, 142 reproduce existing reference errors; these are not successful resumptions. The pre-existing exhausted-budget/pop limitation remains a separate defect.

The fixed CPU prefix preserves 5767258 steps, the historical all-signal state hash, all 921690 ordered publications including timestamp/step/signal/both planes, and 957631 ready pushes/pops. The candidate uses 789614 typed + 609113 generic calls versus 1398727 generic reference calls. Work is identical: 308011 activations, 436016 interpreted PC iterations and 1604701 native charges. These software counts show identical work/ordering; they do not quantify runtime savings.

## Functional correction and changed priority

The first shared-input VCS probe found a pre-existing scalar/wide conditional defect: an ambiguous selector preserved identical Z branch bits, whereas fresh VCS returns X. Disabling typed stores reproduces the same defective timeline. Scalar and multiword merging now preserve only identical known 0/1 bits; known selectors still pass their chosen Z bits through unchanged. The runtime test enumerates all 64 condition/branch states; the independent wide numeric oracle covers limb boundaries through 1024 bits. A same-source VCS probe covers 64 combinations at widths 4 and 129.

The shared fixture also has Active-region displays that observe different legal intermediate scheduling results; these are retained as raw evidence rather than described as matching. VCS comparison checks every settled bit timeline and the final stable line. The standalone conditional probe samples after a delay and checks all 64 complete lines.

At the user's request, work switched to functional completion before formal performance measurement. The development speed screens precede the conditional correction and are not final-release speed claims. No formal installed M132-versus-VCS runtime comparison is claimed. Generic combinational DAG fusion, intermediate-publication removal and grouped NBA propagation remain unfinished; further speed work is deferred.

Installation proofs, final VCS results and archive identities are recorded below after the corrected frozen builds finish their semantic checks.


## Final functional release

Mac release `20261027T161832099595Z-41c1da1fced9` and Intel Linux release `20261027T161914Z-b9f9cfb` are active. The stable Mac entry and both Linux entries resolve to their verified immutable binaries. Each installation regenerated and ran the four original complete CPU/CRC/muldiv/AXI4 workloads, matching all expected outputs, the frozen C++ hashes and all eight runtime headers. These are correctness runs, with no final performance comparison.

Each platform passes the nine-model totals above. Linux also passes 16 CTests including both typed-store kernels, the existing scheduler/checkpoint kernels and 23,496 independent numeric operations. Mac passes the same numeric/runtime tests and three ASan/UBSan programs (native/reference store kernels and the generated 4/129-bit conditional model). The source archive contains 1715 Git-matching members; all 725 Mac publisher input fingerprints match that frozen package.

Fresh VCS comparisons pass all 131 settled bits and the stable final line of the shared-input fixture, plus all 496 settled bits and 64 delayed TRACE lines of the independent conditional fixture. The old pre-fix generic and typed paths share the same four erroneous bit timelines; their failure evidence is retained separately in `known-defect-before.json` and the raw archive. Active display traces are retained but are not described as identical.

`mac-raw.json` / `linux-raw.json` identify member-verified archives of owned inputs, generated models, binaries, waveforms, complete test logs, development screens and source packages. The original vendor build directory stays on 103 and is excluded. Both archives are mirrored to both prefixes under `evidence/m132-region-transport`; `mirrors.json` verifies all four installed copies. `audit.py` checks frozen Git/package identities, publisher inputs, native entries, semantic totals, eight complete outputs, numeric raw output, every raw member and fresh VCS waveforms/TRACE. It records the decision to defer formal performance work.
