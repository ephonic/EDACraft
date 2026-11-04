# M225 — runtime string replication for the unchanged UVM printer

The compiler and RTL parser now support runtime integral repetition of strings,
nested/conditional repeats, sized mixed concatenations and packed conversions.
Counts and payloads evaluate once, including zero/negative counts. Unknown counts
produce empty strings. Constant packed repetitions keep their bit semantics.
Generated code uses a feature-guarded helper with checked allocation and doubling
copies; a 1,048,576-byte result limit is an explicit dsim implementation boundary.

Nine same-byte VCS W-2024.09 fixtures cover literals, variable values, zero/negative/
XZ counts, nesting, conversion widths, object/queue state, wait subscriptions,
wide counts, side effects, legacy packed semantics and a 32 KiB result. The final
normal matrix passes 36 native captures across default/shared/wheel/thread request,
seven compile boundaries and one runtime size rejection. Four forced failed
predictions restore state with complete ordered-wave identity.

Unchanged Accellera UVM 2020.3.1 advances from uvm_printer.svh:1501 to function
$finish in uvm_root.svh:183. Default/shared/sanitized frontends confirm that next
blocker without generating a complete native model. Full UVM/run_test remains
incomplete; process::await is a later known gap. Dynamic repeat $bits still differs
from VCS (result bits versus 1); checks on global side effects in count functions
are not fully aligned. There is no new performance or C910 conclusion.

Raw sources and logs, including initial malformed probe sources and the fixed
compiler/context failures, remain in dsim-test/evidence/m225-string-replication.
Malformed probe errors are not counted as language rejections. No proprietary
VCS-generated code is included in this repository.

Nine sanitized frontends and generated native programs pass ASan/UBSan, with exact
shared C++ and complete ordered-wave identity to the normal matrix. VCS rejects
six of the seven checked compile boundaries but accepts runtime numeric packed
repetition, which remains an explicit dsim gap. The runtime allocation cap is
not classified as a VCS rejection.

Affected legacy string/string-subroutine positives complete 31/46 captures with
four rollbacks each. Their original wrappers subsequently stopped on obsolete
string-to-integer rejections. Those checks are replaced with string-to-real
boundaries; all updated 25/10 negatives pass with protected outputs. Initial
wrapper failures remain external and are not counted as successful exits.
Frozen release checks will rerun the complete updated groups.

Production source 1bd413af is pushed. Mac stable
20261103T011012959339Z-a4f4652d1647 is active from clean frozen sources.
All three complete updated groups pass (113 captures, 42 compile boundaries,
one runtime rejection, eight legacy rollbacks), plus mandatory RTL/format parser
and native DB checks. The 36 new C++ inputs match development. Nine actual entry
emissions match the release inputs; those native artifacts are reused and rerun
with complete ordered-wave identity. 103 Intel stable 20261103T011018160463Z-a4f4652d1647 is also active. Both
root/bin aliases pass. Each endpoint completes the same three groups and mandatory
checks. Source SHA, nine complete actual-entry C++ files and TRACE outputs match
across platforms; both endpoints rerun the native inputs after exact C++ identity
with complete ordered-wave checks. Release and cross-platform receipts are included.
The source commit remains 1bd413af; later evidence commits do not change production.
