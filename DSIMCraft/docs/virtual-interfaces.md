M236 adds [virtual interface task/function calls](virtual-interface-calls.md), including resumable calls, arguments, imported methods and pure automatic event/wait functions. Earlier subroutine exclusions below are superseded within that documented scope.

# Virtual interface handles

M234 adds runtime virtual interface handles to the RTL parser and compiled simulator. The gate netlist parser remains independent.

A handle identifies an elaborated interface instance. Reads, blocking assignments, NBA assignments and scalar ref arguments use that instance's canonical signals; there is no copied interface storage. Rebinding a handle leaves previously captured NBA/ref targets bound to their original storage. A pending event expression observes the current handle, matching the same-source VCS rebind probe. Dereferences in event callbacks are deferred until the wait is armed, so an inactive wait does not dereference the initial null value.

Supported syntax includes `virtual bus_if`, `virtual interface bus_if`, modport-qualified types, typedef aliases, class properties and constructor/formal arguments, function return aliases, null assignment/comparison and generic class type arguments such as `uvm_config_db#(virtual bus_if)`. Whole-interface values may narrow to a modport; incompatible interface types, incompatible views and widening a restricted view are rejected. Reads and writes of scalar and packed members preserve their existing four-state values and signedness; packed selects and compound updates capture the receiver and indices once. Modport input and visibility restrictions apply.

Dependencies conservatively include all compatible elaborated interface instances. Those users share their existing scheduler dependency components. Handles use ordinary simulation values, so checkpoints restore handle bindings along with interface signals, wait state and NBA/ref targets.

The unchanged Accellera UVM 2020.3.1 library now runs a config_db → driver → DUT pins → monitor → analysis scoreboard test. Three factory-overridden transactions carry 100/101/102; both DUT and scoreboard see three transfers totaling 303, with zero UVM_ERROR/UVM_FATAL. Same-byte library/test fingerprints and all TRACE lines match VCS. Verification uses --shared-functions, UVM_NO_DPI and native -O0; it does not establish full UVM or performance compatibility.

Current boundaries: `$cast` of virtual handles (use compatible typed assignment), explicit parameter overrides in virtual-interface type syntax, virtual clocking-block access, interface instance arrays and general unpacked-member transfers are not implemented by this change. Dereferencing a type without any compatible elaborated instance is rejected during compilation. General arrays/containers of virtual handles are not validated as a supported feature. The tests exercise singular handles and scalar/packed members. Complete DPI/VPI, joint object-graph constraint solving, advanced coverage/SVA and full RAL/VIP compatibility remain separate gaps.

Reproducers and validation: [tests](../tests/virtual_interfaces/regression.py), [real UVM DUT test](../tests/uvm_preprocess/virtual_interface.sv), [evidence](../validation/m234-virtual-interfaces/README.md).

The combined [M235 dual stable release](../validation/m235-stream-enums/README.md) includes this implementation; its actual local/103 entries both pass the original DUT, field utilities and wide-packing flows.
