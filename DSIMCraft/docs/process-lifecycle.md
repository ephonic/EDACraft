# Process lifecycle

M228 supports process::self(), status(), kill() and await(), in addition to
existing process random state methods. status returns the process::state enum.
A process handle retains the state of its original incarnation when a fork slot
is reused. Normal completion yields FINISHED, cancellation KILLED; timers and
waiters from cancelled activations cannot restart them. kill also cancels
descendants. Killing the current process unwinds its function/task caller.
await suspends the caller until that incarnation finishes or is killed, and
returns immediately for an already completed handle.

Await is a task statement and is rejected inside functions/final blocks.
Null handles fail explicitly. suspend/resume are still unsupported.
Designs using lifecycle control conservatively use a single scheduling kernel.
Checkpoint and failed prediction restore lifecycle state and await registrations.

The full-library UVM check can be run with:

```sh
python3 scripts/uvm_smoke.py --compiler build/dsim \
  --uvm-dir /path/to/accellera-2020.3.1 --out /tmp/dsim-uvm-new
```

The library must have src/uvm_pkg.sv; output must be a fresh directory.
This compiles the original package and tests/uvm_preprocess/smoke.sv, builds a
native simulator, then runs hello_test and checks its marker/error counts.
The same command accepts `--simulator vcs --compiler /path/to/vcs` after sourcing
the VCS environment. Use `--test /path/to/smoke.sv` for a separate checkout of the
same test (module top). Both paths use UVM_NO_DPI. The report includes a combined
fingerprint for all 181 UVM source files, stage status and live log files.
Each invocation needs a new output directory, so failed attempts remain available.
Timeouts kill the child process group and are reported separately from rejection.
M229 adds [resumable automatic tasks](shared-tasks.md), passing the sequence
call-graph blocker. M230 also passes dynamic queue streaming and array
casts; full UVM now stops at associative array value/output arguments in
uvm_phase.svh:2092. See
[M228 evidence](../validation/m228-process-lifetime/README.md).
