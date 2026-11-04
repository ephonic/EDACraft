# M228 — process lifecycle and full UVM integration checks

Native process::status(), kill() and await() preserve the process incarnation,
wake await/status observers on completion or cancellation, invalidate stale
timers and kill descendants. Self-kill unwinds functions without executing the
remaining caller. Checkpoints own waiters and lifecycle state. suspend/resume
remain unsupported.

Nine same-byte VCS W-2024.09 models match, including dynamic string membership,
a supported randomizable subtype in a hierarchy containing an unsupported rand
object subtype, and an uninstantiated abstract virtual method. The latter fixes
empty virtual dispatch falling back to an unreachable static body. Unsupported
joint object-graph randomization still reports an explicit error when selected;
it is not implemented by this change.

Default/shared native models pass 18 complete ordered captures; six protected
compile boundaries and four explicit runtime failures pass. Three frontend and
native ASan/UBSan probes have identical generated C++ and full waves. Five failed
predictions compare complete waves over identical bounded horizons, including
registered awaiters. The older process handle group passes 110 captures, one
rollback/commit, 15 compile boundaries and seven runtime errors.

The unchanged complete Accellera UVM 2020.3.1 package with the repository's
hello_test passes compilation and run_test on VCS (zero errors/fatals).
dsim passes the process control, derived-randomization dispatch and string-inside
blockers, but still rejects task reentry at uvm_reg_sequence.svh:570:
uvm_sequence_base.start from uvm_reg_frontdoor.start.
No complete dsim UVM native program or run_test success is claimed.

scripts/uvm_smoke.py prioritizes this actual complete-library pipeline. It records
source hashes, compile/native/run stages and logs, and requires the marker plus
zero UVM errors/fatals. It uses UVM_NO_DPI on both simulators; no UVM library edits
or stubs. Frontend-only progress is reported as FRONTEND_BLOCKED.
Raw evidence: dsim-test/evidence/m228-process-lifetime.
No performance comparison or C910 conclusion is made.

Production 800d45f6 is pushed and active on Mac and 103 Intel. Both frozen
releases pass 128 captures, 21 compile boundaries, 11 runtime errors and mandatory
parser/format/native DB checks. All 18 new C++ inputs match development; nine
actual-entry C++ inputs and traces match across hosts with complete native waves.
The first Linux activation used a wrong checker directory and automatically
rolled back. The staged build had passed; the corrected checker verifies the
existing immutable candidate before activation. Initial failure and recovery
receipts are preserved. Both Linux aliases pass.

The fast harness also runs VCS using --simulator vcs --compiler /path/to/vcs.
All 181 UVM source file hashes and the test hash agree across the two simulators;
VCS passes the actual native hello test with zero UVM errors/fatals. A deliberate
one-second compile timeout checks process-group cancellation and explicit
COMPILE_TIMEOUT reporting. No timeout is counted as a feature pass.
