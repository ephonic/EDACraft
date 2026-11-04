# Resumable shared automatic tasks

M229 extends `--shared-functions` to automatic tasks. Each concrete automatic
task has one compiled state machine and each call owns its program position,
arguments, automatic storage, site mappings and return continuation. Class
tasks participate in the same mechanism, including virtual dispatch and super
calls. Static tasks retain the inline path and recursive static tasks remain
unsupported. The mode requires serial simulation.

Calls execute on the caller's simulation process. They do not spawn a process,
consume a fork RNG seed or change process::self(). Delays, event waits and joins
suspend the current task and resume it before returning to the caller.
Input/ref/const-ref and output/inout retain their existing type restrictions;
output copies resolve destinations in the caller's frame, including recursive
calls whose formal variables have the same logical IDs. Background children
retain captured automatic storage after return. Cancellation restores the
original process closure for fork-slot reuse.

Named-block disable distinguishes task invocations as well as PC ranges. It can
unwind a suspended inner task and cancel escaped descendants of task calls made
inside the block. Checkpoints own invocation ancestry and continuations, so
failed predictions replay the same task calls and complete ordered waveforms.
Live shared-task nesting is limited to 1024; exceeding it reports a runtime error.
Private execution records currently grow with calls; this release prioritizes
functional integration and makes no runtime speed claim.

An optional randomize call inside a library function can be compiled even when
its static type needs joint object-graph solving. Executing that unsupported
solver still fails explicitly. This does not implement joint graph solving;
direct unsupported randomize calls retain their compile-time boundary.

The original complete UVM package now passes the sequence.start recursive-task
blocker. M230 also passes the streaming conversion in reg_map and its fixed local string
array. The next blocker is associative array value/output arguments in
uvm_phase.svh:2092.
No complete UVM native program or run_test pass is claimed.
See [M229 validation](../validation/m229-shared-tasks/README.md).
