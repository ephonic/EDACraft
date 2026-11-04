# M223 — REPORT-GAP13 function background forks

The exact `/tmp/ff.sv` probe from REPORT-GAP13 was preserved and reproduced:
M222 rejects `fork` in a function. The new implementation permits `join_none`
while retaining direct timing restrictions on the function itself. Child bodies
are ordinary compiled processes and can wait, delay, invoke tasks and nest forks.
A function fork is a template instantiated under the runtime caller, including
startup calls. Active children retain the immutable automatic frame chain;
finished sites and storage can be reused without aliasing live calls.

Nine same-byte VCS W-2024.09 fixtures check the original probe, returned values,
live automatic locals, overlapping calls, the UVM-style queue listener/guard,
parent-local wait/cancellation, nested function/ordinary forks, startup calls,
repeated reuse, scalar ref/const-ref aliases and transitive wrappers retaining
a local passed by reference. Background effects propagate through expressions,
constructors, virtual dispatch and declaration initializers. The first VCS negative wrapper
correctly rejected five invalid function controls, then stopped because VCS only
warns about direct reference capture (SV-IATRA). That conservative new rejection
was removed, a reference positive added, and the five identical rejection hashes
are retained. No successful six-negative oracle is claimed.

Function background ownership can vary by caller. Designs requesting threads
currently fall back to one kernel and report that fact; these tests do not count
as real parallel execution. Direct joins/join_any, delay, wait and wait-fork in
functions remain rejected. Function `$finish`/`$stop`, event copying, associative
array arguments and runtime string replication remain separate report gaps.

Persistent raw evidence: `dsim-test/evidence/m223-function-forks`; oracle logs
remain under isolated `/tmp/dsim-m223-*` paths on 103. The user's report and
original failing probe are preserved there. No VCS-generated implementation is
copied into the repository and no new speed comparison is claimed.

The final nine-model matrix passes 36 native captures with complete ordered
waveforms across default/shared/wheel and requested-thread serial fallback.
Six dsim compile diagnostics protect pre-existing output. Five have identical
VCS rejections; a final-block background-spawn probe is accepted by VCS and stays
an explicit dsim boundary, not a matched oracle rejection. All nine frontend and
native ASan/UBSan builds pass, with exact shared C++ and complete-wave identity.
Six failed predictions restore captures/ownership/waiters, including a transitive
wrapper; repeated calls also check bounded signal/process allocation.

Old dynamic-fork/control groups were freshly built and ran 111/99 captures with
three actual rollbacks each and real two-partition execution. After the final
background-effect propagation change, all 51 of their generated inputs remain
byte-identical; those native results are reused, not rerun or counted again.
The report's patched library advances to `process_guard:152` (`process::await`);
the unchanged full public library still fails event assignment in all three
frontend configurations. See `REPORT-GAP13-CURRENT.md` for the report audit,
including the existing legal nested-replication support rechecked against VCS.

Production `17986884` is pushed. Mac stable
`20261102T153701447796Z-cd71c851a0b5` and 103 Intel stable
`20261102T153655290004Z-cd71c851a0b5` are active from clean frozen inputs.
Each endpoint passes both selected groups (69 native captures, 13 dsim compile
diagnostics and two runtime rejections), plus mandatory parser, format and native
DB checks. All 36 new generated C++ inputs match development. Twenty actual
stable-entry emissions match validated native inputs on each endpoint; those
native programs are reused and rerun with complete ordered-wave identity.
Both 103 root/bin aliases are checked. Common source SHA and all twenty full
actual-entry C++ files/TRACE outputs match across platforms. See release receipts
and `cross-platform.json`; no full UVM or new performance result is implied.
