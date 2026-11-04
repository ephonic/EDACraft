M234 adds [virtual interface handles](virtual-interfaces.md), including class properties, modports, events, NBA/ref capture and a real UVM DUT path. The virtual-interface exclusions in the historical M84/M141/M144 notes below are superseded within that documented subset.

# Interface / modport

M84 adds interface instances to the RTL parser and elaborator. The gate-netlist parser remains separate. Interface members use the actual instance's existing signal and memory storage; a module's interface formal owns no copied signal storage.

Supported:

- Named, parameterized interface definitions with ordinary integral ports, signals, fixed unpacked arrays, packed aggregates, enums, initial/always blocks and continuous assignments accepted by the RTL backend.
- Typed interface formals, typed modport formals and generic `interface` formals in ANSI module headers. Ordinary and interface formals may be interleaved; consecutive interface identifiers may share a header.
- Positional and named connections, direct instance connections and explicit `instance.modport` connections. Interface formals can be forwarded through wrapper modules. A forwarded or explicit view remains constrained when received by an unqualified formal.
- Blocking/NBA writes, packed and unpacked element selection, enum methods and sensitivity through the actual interface storage. Interface tri nets use the existing four-state multi-driver resolver.
- Modport input members are read-only through that view. Invisible members, unknown views, incompatible views/types, duplicate connections and missing interface actuals are rejected. Direct testbench writes to actual interface members remain possible. Ordinary module hierarchical references retain their existing read-only restriction.
- Existing time-wheel scheduling, checkpoint/failed prediction rollback, waveform capture and dependency partitioning operate on canonical interface signal IDs. A shared interface joins its users' dependency components; independent lanes can run in separate worker partitions.

Declare interface instances before connecting them. VCS treats an earlier undeclared connection identifier as an implicit wire, then rejects its later interface declaration; that failed development fixture is retained in the validation directory. For mixed plain typed formals, declare the interface definition before the module header so lexical type disambiguation can recognize it.

Not implemented: interface instance arrays, interface ports in module instance arrays, virtual interfaces/classes, clocking blocks, modport subroutine exports, interface inheritance and full verification-library support. Unsupported constructs are not claimed as VCS-compatible. The implementation does not add full SystemVerilog or full concurrent SVA support.

Verification uses eight same-source models, full ordered captures across serial/time-wheel/parallel execution, forced failed predictions, negative cases and actual VCS runs. See [M84 evidence](../validation/m84-interfaces/README.md) for measured results and exact waveform coverage.

M141 adds task/function calls through actual interface instances and typed, generic or forwarded interface ports. Modports may import subroutines by name (`modport client(import read, write, input value)`). Only imported names are callable through a constrained view; signal input restrictions still apply to caller-side output/ref actuals, while an imported routine executes in the actual interface lexical scope. Existing positional/named/default arguments, scalar/string/array signatures, automatic/ref storage, static locals and zero-time function restrictions are reused. Existing ref-actual restrictions still apply; arbitrary hierarchical expressions are not accepted as ref actuals. Interface task delays use the interface timescale, including calls made from a module with a different timescale. Return width, signedness, enums, packed structs and string type metadata are preserved.

See [interface subroutine tests](../tests/interface_subroutines/regression.py) for executable scope and rejection cases. M144 additionally supports prototype-form imports; exports, virtual interfaces, interface arrays and full verification-library compatibility remain outside the implemented subset. See [modport prototype imports](modport-prototypes.md) for signatures and view defaults.
