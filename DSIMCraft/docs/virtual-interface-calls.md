# Virtual interface subroutines

M236 adds task/function calls through virtual interface handles. The RTL parser
binds the declared interface signature and modport import permissions. The
compiler binds each compatible elaborated instance separately and dispatches at
runtime to its actual lexical scope. No interface data is copied or replaced by
class fields.

Functions preserve their scalar, signed, enum, wide, real, string and supported
unpacked-array result representation. Arguments reuse existing named/default,
input/output/inout and scalar/array ref semantics. Tasks reuse the normal
resumable automatic frames and caller process identity, including delays,
reentry and calls nested inside class methods. A selected task retains its
instance while suspended, even if the caller rebinds its virtual handle. Static
method locals remain per interface instance. Delays use the actual interface's
time unit and precision.

Effect-free automatic functions can be used in event and wait expressions.
Explicit arguments determine wake sensitivity; body reads still constrain the
process dependency graph. Nullable receiver callbacks are deferred until the
wait is armed. Side effects and virtual class dispatch in event callbacks retain
the existing rejection boundaries.

The unchanged Accellera UVM 2020.3.1 DUT test now calls `vif.drive()` in the driver
and `vif.active()/sample()` in an independent monitor. Three factory-created
transactions (100/101/102) yield three DUT transfers and scoreboard sum 303 with
zero UVM_ERROR/UVM_FATAL, matching the same-source VCS run. Tests use
`--shared-functions`, `UVM_NO_DPI` and native `-O0`; this is not complete UVM or a
performance comparison.

Known differences are retained. When an argument rebinds the receiver's final
virtual-interface slot, dsim snapshots that slot before arguments; VCS in the
retained probe reads it afterward. Both evaluate the base receiver function once.
VCS accepts the retained side-effecting event-function probe which dsim rejects.
VCS also executes the null-interface function probe while dsim diagnoses it;
both reject the null task call. These are not counted as alignment passes.

Explicit virtual-interface parameter overrides, virtual clocking access,
interface instance arrays and the other documented virtual-handle boundaries
remain separate work. See [handles](virtual-interfaces.md),
[tests](../tests/virtual_interface_calls/regression.py),
[original UVM test](../tests/uvm_preprocess/interface_calls.sv) and
[validation](../validation/m236-interface-calls/README.md).
