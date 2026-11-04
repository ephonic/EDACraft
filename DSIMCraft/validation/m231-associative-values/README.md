# M231 — associative value arguments and late virtual dispatch

Whole associative input/output/inout arguments use owned snapshots, independent
activation storage and normal-return copyout. A resumable task snapshots its
output before switching to its caller's activation. This covers recursive calls
whose caller and callee use the same logical formal IDs. Multidimensional trees
and queue leaves are copied; object handle identities remain shared.

Ten same-byte fixtures match VCS W-2024.09: private input, delayed output/inout,
class keys, class-owned maps, functions, recursive functions/tasks, concurrent
calls and multidimensional/subarray arguments. Serial/shared/shared-wheel modes
pass 29 native executions and complete ordered waveform comparisons; recursive
tasks use the two shared modes. Four compile boundaries preserve pre-existing
output files; all four are also rejected by VCS. Six frontend/native ASan/UBSan models and five equal-horizon failed
prediction scenarios pass. Final frontend C++ identity is checked separately.

Late class binding could introduce a concrete type after an earlier virtual
dispatch was lowered. Lowering now closes the discovered class universe before
emission, rebuilding IR and effects against the complete set; class seed order
uses stable IDs. `virtual_closure.sv` reproduces the previous runtime exception
and now matches VCS (`50 2`). Existing late binding regression includes it.

Obsolete rejection cases for associative inputs and class string maps are
removed; the mixed-container diagnostic is updated to its current wording.
Existing positive class string-map tests remain in their own group.

Unchanged complete Accellera UVM 2020.3.1 with UVM_NO_DPI (181 source files, tree
SHA 65296510b8010f96fccb3cd294936a68ec1fc7f71c9fe540af181bfddf45fe6f)
now emits a complete C++ model and compiles an -O0 native verification program.
It passes the former phase output-map frontend blocker and initialization's
late-type virtual dispatch failure, then stops with `invalid reference argument
binding`. The actual is a scalar class field; the current compiler mistakenly
uses the object heap signal as its ref storage. No REAL_UVM_SMOKE marker or
run_test pass. The library is unchanged and has no replacement implementations.
The earlier VCS smoke uses identical source fingerprints and passes.

Native -O0 verification and the original -O2 attempt are recorded separately.
The original -O2 model also compiled successfully and then hit the now-fixed
late-type dispatch exception; it does not validate the final runtime path.
This is functionality evidence, not a same-machine compile/runtime comparison.
Raw evidence: `dsim-test/evidence/m231-associative-values/`.

Production 42290424 is pushed. Mac 20261103T181556448407Z-9ba5ccd88182 and
103 Intel 20261103T181638314409Z-9ba5ccd88182 are active. Each frozen release
passes five groups (336 captures, 49 compile boundaries, one runtime rejection)
and mandatory parser/format/native DB checks. All 29 new C++ files match the
validated development inputs; eleven actual-entry C++/traces match across
hosts, with complete per-platform wave reruns. Both 103 aliases pass.

Both actual stable entries reproduce their complete UVM models byte-for-byte
before reusing the validated native -O0 program and hitting the same scalar ref
failure. No run_test pass. The next scalar-field ref probe passes VCS (pending 7,
final 9) and fails dsim with the same binding diagnostic, recorded as a gap.

The first 103 activation attempt used an incorrect actual-entry helper directory;
it automatically restored M230. The corrected helper path was checked against
the same immutable, fully tested candidate, then reactivated with both aliases
and actual-entry verification. Initial failure and recovery receipts are retained;
no production binary or compiler input changed during recovery.
