# M72: reported frontend compatibility fixes

The three reported compatibility gaps are implemented: multidimensional packed
ports/variables and indexing, generate prefix/postfix increments/decrements, and
root inference without requiring the name `top`. An explicit Verilog keyword
mode also permits ordinary identifiers such as `ref`; default SystemVerilog keeps
that keyword reserved and accepts escaped identifiers. See
[usage and boundaries](../../docs/frontend-compatibility.md).

The separate gate parser is unchanged. Packed AST ranges retain each dimension
through semantic analysis and parameterized module clones; the storage ABI stays
linear. Constant selections generate direct offsets. Runtime selections use the
existing once-only index expression and central bit-selection/NBA machinery,
after checking every dimension. No new scheduler, checkpoint state or persistent
selection buffers were introduced.

Results:

- Twelve final models pass native serial, time-wheel and two-thread backends:
  147 VCD/DWF ordered/settled captures, three failed-prediction rollbacks,
  eight rejection cases and two root selection cases. The parallel model checks
  two executed partitions and both independent expected outputs.
- Actual VCS W-2024.09_Full64 on `10.131.254.103`, after sourcing
  `/apps/EDAs/syn.bash`, passes all twelve final source models and TRACE values.
  Nine timed models additionally match **all 1,171 exported physical-bit settled
  timelines**, with no bit exclusions. Two 16-bit read-only memory observers and
  normalization of five escaped generate VCD identifiers are recorded explicitly.
  Three zero-time keyword models are TRACE-only because their `$finish` can
  precede the independent waveform dump initial block.
- Sixteen distinct relevant CTest checks passed across final targeted runs:
  frontend, parser, generate, array queries/copy/dynamic copy, packed/indexed
  selections, variable/array ports, named types/signatures, fixed/dynamic
  initializers, gate CLI/SDF smoke and the six reported external-case fixtures.
  The 14-check first run had one stale negative: multidimensional unpacked
  declarations were already accepted by the previous stable binary. It was
  replaced by an invalid genvar update rejection; the complete generate test
  then passed. The frontend harness's initial repeat-run failure due to existing
  wave files was corrected by deleting only test-owned outputs; final frontend
  CTest passed in 100.28 seconds.
- Eleven sanitized compiler generations and executed generated programs pass
  ASan/UBSan, byte-identical generated C++, and complete ordered stream/stdout
  comparison. This includes seven frontend programs, four fixed-initializer
  programs and actual parallel programs in both groups. Repeated parser
  analysis/clone/cleanup also passes sanitizers. Leak detection was disabled.

Native and sanitizer reports are `native-results.json` and `sanitizers/`;
vendor inputs, commands, source hashes, logs and waves are in `vcs/`.
`vcs-bit-results.json` records the strict comparison. Reproduce it with
`python3 validation/m72-frontend-compat/verify.py`. The public regression entry is
`ctest --test-dir build -R '^rtl_frontend_compat$' --output-on-failure`.

The partial-range probe initially exposed a real VCS difference: the first dsim
implementation clipped invalid multidimensional ranges, whereas VCS read an
entire X selection and suppressed the entire write. `probes/` retains the
pre-alignment source, both outputs and the raw VCS diagnostic probe. The final
implementation and fixtures match the observed VCS policy. The one-dimensional
packed selection path retains its earlier clipping behavior; this does not claim
complete IEEE language conformance.

Several non-`top` roots still require explicit `--top`; a root named `top` retains
legacy preference. Complete SV keyword/version conformance, arbitrary indexed
expression results, subsequent subscripts after a part-select, general variable
output/inout port slices and complete array type compatibility remain outside
this change. No new performance benchmark, full CTest run, or Linux native build
is claimed for this batch. Stable publication is recorded below after its release
checks completed.

## Stable publication

Implementation commit `6f0361b8ed9a2d60729bf93ff89fbd5241e2edb6` was published
to `~/vibe-coding/dsim-test/bin/dsim` after all 25 release checks passed,
including the six reported cases and gate CLI/SDF checks. `stable-release.json`
records the immutable runtime snapshot and complete input hashes;
`stable-publish.json` is the publisher summary and `stable-reported-cases.json`
contains the six-case results. Binary SHA256:
`529e0858354c97c37a3a4e7750df7d217504607b01a353e9610190c041864bc5`.
The dirty flag records the preserved, untracked user `experiments/matvec16/`;
it was not staged or included in the compiler inputs.

`stable-identity.json` confirms byte-identical complete generated C++ and stdout,
plus identical complete waveform streams for 15 frontend/fixed-initializer
programs. The publisher uses default settled capture for the two Verilog keyword
models and ordered capture for the other 13; comparisons use the matching native
capture mode. Both actual parallel models are included.
