# M226 — function termination and resumable stops

Function/method/constructor finish unwinds callers with RAII cleanup, preserving
immediate ref writes while skipping return assignments and output copyout.
Twelve same-byte VCS W-2024.09 sources cover call chains, recursion, virtual
dispatch, constructors, initialization, final blocks and stop commands. Twenty
input paths distinguish normal/startup/final phases and run/quit/EOF. Final finish
is ignored; stop remains active in final. Startup exits skip finals. Normal quit
runs finals; EOF does not. This is basic execution control, not complete UCLI.
Terminating designs use one kernel; old final/bind still checks real two partitions.

Eight dsim compile boundaries are separately classified: VCS rejects three and
accepts five (extra finish/stop arguments, zero-time tasks, NBA in functions).
Those accepted forms remain gaps. The 0/1/2 restriction is an implementation limit.

Raw evidence is in dsim-test/evidence/m226-function-termination. Initial probes
corrected startup/final semantics. A first wrapper attempted waves on models
with no integral signals; those four now execute without wave capture. Another
wrapper reached the virtual fixture using instance, a keyword rejected by dsim
but accepted by VCS. That parser boundary is not fixed here: final fixtures use
derived, rechecked with VCS. Failed wrappers remain raw evidence, not successful
exits. No proprietary VCS-generated code is included in this repository.

Unchanged Accellera UVM 2020.3.1 advances from root:183 to associative array
arguments in resource_pool:178 with normal/shared/sanitized frontends.
Full UVM/run_test remains incomplete; process::await is a later gap. No new C910
or performance conclusion is claimed.

The final normal matrix passes 80 native executions and 56 complete ordered-wave
captures, with eight protected compile boundaries. Four signal-free models run
without wave capture. Legacy final/bind passes 49 captures, eight rollbacks, nine
compile boundaries, real two-partition cases and its coordinator kernel check.
Four forced failed predictions and three external stop barriers pass; repeated
run() executes finals once.

Twelve sanitized frontends and native programs pass (20 native input paths, 14
wave captures). Eleven completed sanitized models from the first wrapper are
reused only after exact full C++ and full-wave comparison with the final normal
matrix; the corrected virtual fixture is separately rebuilt and run. The earlier
parser failure is preserved and not counted as a successful wrapper exit.

Production 297d8a7a is pushed. Mac stable
20261103T015234415106Z-add4cec794cb is active from clean frozen sources.
The two complete groups pass 105 captures and 17 compile boundaries, plus mandatory
RTL/format parser and native DB checks. All 48 new C++ inputs match development.
Twelve actual-entry emissions match the validated native inputs; those artifacts
are rerun over all 20 input paths, checking all 14 applicable full ordered waves.
103 Intel stable 20261103T015241043026Z-add4cec794cb is also active from the
same source hash. Its complete two-group checks pass the same 105 captures and
17 boundaries, plus mandatory parser/format/native DB checks. Both root/bin
aliases pass. Twelve full actual-entry C++ inputs and all twenty input traces
match across platforms; receipts include the per-platform ordered-wave checks.
Production remains 297d8a7a; later evidence commits do not alter the binary.
