# Shared generated function bodies

`dsim --shared-functions tb.sv -o simv` generates one C++ body per lowered
function specialization, with a frame at each call. It is an opt-in serial RTL
mode; the default inline generator remains available. Waveforms and the time
wheel are supported. `--threads` with this mode is rejected explicitly.

This addresses large verification call graphs: repeating the same callee in
several callers no longer repeats its entire generated body. Automatic locals,
return values, references and class receivers are saved and restored by the
owning simulator. Static state persists. Arguments retain their existing
once-only evaluation and copy-in/copy-out behavior. Unsized fixed array formals
retain specialization for their actual bounds. Function bodies run within the
existing process activation; this does not add a scheduler thread or change
simulation time. Recursive input/ref/const-ref scalar and array arguments are
supported; recursive function output/inout arguments and array results remain
unsupported. Automatic tasks use the [resumable shared backend](shared-tasks.md). Recursive native activations have a depth guard of 1024 per
recursive body. The mode does not implement missing SystemVerilog language or
UVM APIs.

The write-range dependency metadata is also deduplicated for both modes. This
removes repeated analysis records without removing or reordering assignments.

Regression `rtl_uvm_call_values` compares full TRACE and ordered VCD across
inline, shared and shared + time-wheel execution. It includes recursive class
queues and arrays, failed prediction replay, class conditional expressions,
parameterized factory aliases, no-parentheses calls and literal escapes. A
26-level repeated call graph checks generated size and the resulting value.
The standalone validation script `validation/m214-uvm-functions/shared-dpi.py`
checks the existing actual C ABI/callback fixtures and late DPI discovery.

Unmodified Accellera UVM 2020.3.1 is still incomplete: the smoke test currently
stops at associative array value/output arguments in `uvm_phase.svh:2092` (M230). Package preprocessing and
individual factory-related regressions are not a complete UVM run.
