# M229 — resumable automatic tasks

Shared mode compiles automatic tasks once, including recursive/mutually
recursive calls across virtual dispatch, super calls and fork processes.
Per-call continuations retain the caller's process identity and automatic
storage. Output copyout uses caller context. Cancellation restores the original
closure for reuse, and named disable uses invocation identity as well as PC.
Invocation ancestry also cancels escaped children from calls inside the block.

Twelve same-byte VCS W-2024.09 fixture outputs match. Shared/time-wheel modes pass
24 complete ordered captures, two protected compile boundaries and two explicit
runtime errors. Six sanitized frontends and actual generated native models pass;
their complete C++ and waveforms match normal runs. Five forced failed predictions
pass equal-horizon full-wave comparisons, including suspended recursive tasks,
fork reentry and cancellation. Old lifecycle tests pass 18 captures/6 boundaries/
4 runtime errors. Old UVM call values pass 22 captures, one rollback and five
boundaries, including the 26-level shared-function graph.

Initial probes exposed parser task expansion cycles, recursive output copyout,
a class-only probe without observable wave signals and named disable copying
unrelated task-template groups. Their failed runs are preserved. The first
sanitized wrapper finished all native runs before normal reference files were
ready; separate completion checks verify its recorded successful executions,
full C++ identity and waves after both suites finish. It is not recorded as a
successful original wrapper.

Old function-background forks also pass their complete regression.

Historical automatic-subroutine negatives included an obsolete recursion
diagnostic and rejected now-supported function display/module static syntax.
The 22 current rejection cases pass a protected-output preflight. Original
failed wrapper logs remain; the frozen release passes the corrected complete
group with 75 captures, three rollbacks and two independent partitions.

Unchanged complete Accellera UVM 2020.3.1, using all 181 source files with the
same fingerprint as the prior passing VCS oracle, now passes sequence.start
task reentry. Normal and sanitized frontends stop at uvm_reg_map.svh:2160:
the dynamic queue stream/array-cast conversion. No complete dsim UVM native
program or run_test success is claimed. Optional unsupported object-graph
rerandomization inside library functions now rejects actual execution instead
of preventing compilation of unused paths; joint solving is still unsupported.

Raw evidence: dsim-test/evidence/m229-shared-tasks. No performance/C910 claim.

Production e5a6ee11 is pushed. Mac 20261103T125008395889Z-301b8da995a8 and
103 Intel 20261103T125021219814Z-301b8da995a8 are active. Both frozen sources
pass five affected groups: 175 captures, 41 compile boundaries, six runtime
rejections and mandatory parser/format/native DB checks. All 24 new C++ inputs
match development; twelve actual-entry C++ inputs and traces match across hosts
after native reruns and full-wave checks. Both 103 aliases pass. Both actual
stable entries reproduce the same next UVM blocker with the original 181-file
library fingerprint and UVM_NO_DPI; neither generates a complete UVM model.

An auxiliary concurrent ref task passes wait(condition) followed by a named-event
wait at the actual Mac entry, with the same-byte VCS output; it is separate from
the twelve-model release group. The next stream blocker has a small same-byte
reproducer in probes/next-stream.sv: VCS produces TRACE dynamic_stream 16 e3fc,
while dsim rejects array copy. This probe remains a recorded gap, not a pass.
