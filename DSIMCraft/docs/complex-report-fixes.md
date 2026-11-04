# Complex RTL report fixes (M86)

Input report: `~/vibe-coding/dsim-test/rtl-tests/complex/REPORT.md`, dated
2026-10-25. The supplied `/home/yangfan/...` path was not present on the remote
host; the local report and its exact 17 probes and six complex designs were used.
The original RTL, testbenches and memory input are copied without edits into
`tests/complex_report/`. The six earlier testbench bugs described by the report
were already fixed in those source files and are not simulator fixes here.

| Report issue | Implemented behavior | Boundaries |
| --- | --- | --- |
| Runtime recursion | Direct recursive automatic integral functions, independent activation frames, including repeated recursive calls and locals | Scalar input arguments; no recursive tasks, mutual recursion, ref/output/array arguments; depth limit 1024 |
| Constant function calls | A separate bounded interpreter evaluates pure integral calls in parameters and ranges | Assignments, return, arithmetic, conditionals and for/while/do loops; no runtime/nonlocal state, nested calls or full constant-function language; 100000-step budget |
| Procedural sampled functions | `$sampled/$past/$rose/$fell/$stable/$changed` use the enclosing single-edge always/always_ff clock; optional `$past` depth and gate | Explicit single static clock, no asynchronous/multiple clock inference; histories advance even when conditional code skips the call |
| force/release | Whole static signal force, reactive RHS, replacement ownership, NBA suppression; released variables retain value and nets resume drivers | Static integral RHS only (no function/memory calls); no partial, concatenated, dynamic, automatic/ref targets or aliased net force |
| Unpacked struct | Fixed integral fields, member access, arrays, same-type copy/equality, `$bits`, mixed bit/logic defaults and field conversion | No string/dynamic members or claim of complete aggregate semantics; integral arithmetic/casts rejected |
| `$writememh/$writememb` | Fixed one-dimensional arrays, wide/four-state words, optional start/end, explicit file addresses | Literal filenames; prediction writes are buffered, rollback discards them and speculative reads see the buffered content |
| Parameter/genvar selects | Constant bit/part/indexed selects and dynamic selects of one packed dimension, including ascending ranges | No multidimensional parameter selection |
| Redeclarations / DEBUG | Reject ANSI port duplicates, repeated variable declarations and mismatching legacy port declarations; retain valid non-ANSI split ports | No unconditional parser DEBUG output |
| Opaque diagnostics | Relevant parser error codes describe constants, ranges, calls and duplicate declarations | Other unsupported language constructs still require separate implementation |
| Execution budget | Says the budget was exhausted and a zero-delay loop is one possible cause | Does not claim to have proven an infinite loop |
| Assertion action blocks | Existing begin/end action support is exercised with actual pass/fail actions | Existing single-clock SVA subset remains; no full sequence language claim |

Run `python3 tests/complex_report/regression.py build/dsim /tmp/complex-check`.
It checks exact output for all 17 probes, all six complex designs, eight boundary
models across serial/time-wheel/threads backends, full ordered waveform identity,
three failed prediction replays, 16 rejected sources and budget diagnostics.
The standard stable publisher also runs this regression before switching its entry.

VCS comparison uses the same source bytes. VCS W-2024.09 rejects three original
probes for declaration initializers combined with always_ff unless its suggested
`-ignore initializer_driver_checks` option is enabled. Both initial rejection
logs and compatible runs are retained; successful process exit alone is not a
passing simulation (VCS may return zero after `$fatal`).

One additional, separately reproduced boundary differs: dynamic out-of-range
selection `integer_parameter[i]` with `i=99` returns 0 in this VCS version,
whereas dsim returns X. VCS returns X for `logic_parameter[i]` and for the constant
`integer_parameter[99]` select. This difference is recorded rather than counted
as parity. It does not affect the report's in-range `DEPTH[3:0]`/`g[7:0]` cases.
Another diagnostic-policy difference is retained: this VCS version emits
`Warning-[IPDW]` and ignores redundant identical ANSI port/variable declarations.
Following the input report's requested behavior, dsim rejects them with a semantic
error; valid legacy split-port declarations remain accepted. These negative
checks are not claimed to match VCS's warning severity.

No DWF encoding changes or performance improvement claims are part of this fix.
