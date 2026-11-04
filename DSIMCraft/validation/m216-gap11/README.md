# M216 — REPORT-GAP11

Input: `dsim-test/rtl-tests/complex/REPORT-GAP11.md`, dated 2026-11-02,
which tested M214 (`20261101T145923006249Z-060aedf5c606`). This batch builds on
M215; the report's inference that all UVM language gaps have disappeared is not
supported by actual compilation.

## Changes

- Fix four unpacked array equality operators, equivalent element/container type
  checks, four-state decisions, string/struct/handle values, fixed axes and
  single evaluation of function operands.
- Preserve intermediate direct array comparison events within one activation;
  keep normal process scheduling and prediction rollback.
- Accept contextual struct assignment patterns for queue element arguments.
- Permit explicit-format `$swrite`/`$sformat` within functions.
- Add string foreach, including property character reads and loop control.
- Bound inline function expansion and automatically retry serial RTL using
  shared function bodies. The unchanged UVM library now fails promptly with a
  concrete next semantic gap under the default invocation.
- Coalesce repeated signal registration statements. The original standalone
  144-bit SRAM frontend was already finishing in about 0.35 seconds; its old
  native Clang compile exceeded 180 seconds. A development build with the fix
  compiled the same original four-file invocation in about 14.8 seconds;
  the final Mac stable entry took 0.207 seconds for the frontend and 16.002
  seconds for the complete native invocation.
  These are local observations, not a dsim/VCS speed ratio.

## Report audit

| Item | Result |
|---|---|
| P1 module static, P3 synthesis comment, P4 duplicate module | Existing M213 fixes retained; C910 frontend regressions rerun |
| P2 `{{N{X}}}` | Legal; native dsim/VCS fixture matches |
| P2 `{N{1{X}}}` | VCS also rejects this exact syntax; retain rejection. Legal nested form is `{N{{1{X}}}}` |
| P5 standalone 1024×144 SRAM | Frontend and native compilation separately measured using original files; see SRAM receipt |
| P6 all diagnostic infrastructure | Still partial; no claim of fixing every global-line/macro location issue |
| rand enum | Anonymous/named, scope and wide enum randomization rerun successfully; non-scalar object graph randomization remains limited |
| Full original UVM | Incomplete. Default retry and explicit shared mode reach the next array-value argument gap in the field macro at `uvm_reg_mem_hdl_paths_seq.svh:67`; no generated native model or `run_test` success |

## Validation and evidence

`vcs.json` records nine same-byte fixtures and exact traces from VCS W-2024.09;
`oracle-evidence.json` also locates the archived raw sources and traces and
verifies all nine source hashes against that receipt.
`tests/array_equality/regression.py` checks three native modes and complete decoded waves, a failed
prediction replay, thirteen specific rejection diagnostics/output protection,
and a 26-level diamond that defaults to shared bodies and runs to 92.
`sanitize.py` checks the actual frontend, generated native programs and parser
reset on the default retry with ASan/UBSan. `sram.py` compiles the unchanged
external source files and records their hashes. Candidate and activation
receipts are added only after the corresponding steps pass.

Raw local work is under `/private/tmp/dsim-m216`, with final persistent evidence
archived outside the source tree before completion. Initial failures are
retained: a reused CTest output directory rejected an existing waveform; the
first event probe exposed the transient comparison bug fixed here; an initial
hierarchical generated-bank observer is unsupported in both M215 and this
batch; large wave-enabled RAM registration compilation was terminated while
working on the report's default non-wave path. The committed registration
fixture uses 32 elements per bank and portable output-port observations, while
the original 144×1024 non-wave case is checked separately. None of these initial
attempts is counted as a passing final regression.

Additional remaining limits include generated-scope array element hierarchy
in that observer, mixed integral/string concatenation, associative/real array
equality, pending NBA array comparison events and the unchanged public UVM's
next array argument context. Full C910 is not rerun in this batch; the prior
minimal RV64 TEST PASS remains the last full-design run evidence. No runtime
performance campaign or new VCS runtime ratio is included.

## Final entry checks

The production revision is `02e66b25c99afa6118a9131b9e44629c24b1f0ed`,
with 1,540 release inputs and source SHA
`18430abc55fe2661351fd5ad015b5c8a01174a2cbe58207726354ca6e5792c5c`.
Mac stable entry `dsim-test/bin/dsim` is activated at
`20261102T022208066821Z-18430abc55fe`; actual entry native/wave checks and the
nine C910 frontend models with six output-protected rejection diagnostics pass.

The report's original, unchanged `hello.sv` is separately checked with
`--top tb -o smoke`, including its class registration and `run_phase` code.
Default compilation now returns the next semantic error in 0.942 seconds with
190,480,384 bytes maximum RSS; explicit shared mode takes 0.750 seconds with
184,532,992 bytes. These are bounded failures, **not UVM passes**. Both stop at
`uvm_reg_mem_hdl_paths_seq.svh:67: array value requires an unpacked array expression`.
The separate public-library smoke keeps the exact 166-file preprocessing
identity; its default peak is 176,373,760 bytes. ASan/UBSan frontend and nine
generated native programs, complete shared-wave identities, thirteen negative
cases and parser reset/retry pass. Enum checks and affected/event regression
receipts are also retained here.

The first 103 release build hit the configured 600-second build-command limit
before creating a binary; it was never activated. Its failure logs and receipt
are preserved and its two identified orphan compiler processes were terminated.
The second build reached the 2,400-second whole-build limit after producing
dsim, while still compiling a mandatory parser test. `recover-stage.py`
preserves that second failed receipt, waits for the identified existing build
children, and resumes the **same candidate directory** with unchanged frozen
inputs, compiler options and all original mandatory/five-group assertions.
It uses 3,600 seconds for the incremental remainder and 2,400 seconds for each
regression command. Both initial failures remain recorded; neither failed
state is activated. Linux activation and cross-platform results are recorded
only after their checks pass.

Linux completion: the complete three-mode matrix passed with explicit native
`-O0` functional builds; all original assertions were retained. Mac used the
normal `-O2` builds. The 68 generated C++ files and 65 complete decoded captures
are identical across platforms (`cross-platform.json`). The formal compiler's
default remains unchanged. Four actual-entry models also pass with `-O2`
native artifacts and identical source/trace/full-wave hashes. The registration
driver hit its 600-second wait limit, but its completed executable was retained
and verified before reuse. `activate-cached.py` re-emits through the actual
entries and requires byte-identical C++ before running each native artifact;
this is not a claim of four fresh native compilations on the retry.

Both 103 entries now select `20261102T023546176998Z-18430abc55fe`;
`linux-activation.json` and `linux-native-reuse.json` record the checks. Raw
functional results, timed-out attempts and compiler commands are archived at
`dsim-test/evidence/m216-gap11/linux` alongside the Mac/oracle evidence.

Additional stable-entry probes: the original public UVM and report hello_test
return the expected bounded next semantic blocker; nine C910 frontend models
pass as explicit `-O0` functional builds. The original SRAM frontend passes on
103, but its default `-O2` native compilation exceeded the 600-second probe
budget. This is retained as a timeout, not a successful remote native compile
or a VCS speed comparison. The Mac original-source native receipt still passes.
