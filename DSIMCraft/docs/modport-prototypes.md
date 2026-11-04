# Modport prototype imports

M144 extends the RTL parser's interface support with `import task` and `import function` prototypes. Gate-level parsing remains separate. VCS rejects mixing by-name and prototype imports in a single clause; DSIM accepts this combination, and its timing fixture is listed as reference-unsupported. Prototype nodes are owned by each interface AST and cloned with the actual parameterized instance; they do not allocate simulated interface state or export a second callable definition.

```systemverilog
interface bus #(parameter W=8);
  logic[W-1:0] value;
  modport client(import function logic[W-1:0] read(input integer n=7),
                 task write(input logic[W-1:0] data), input value);
  function automatic logic[W-1:0] read(input integer n=1);
    return value+n;
  endfunction
  task automatic write(input logic[W-1:0] data);
    #1; value=data;
  endtask
endinterface
```

A prototype may precede the implementation, coexist with by-name imports, and use built-in or lexically visible typedef return/argument types supported by ordinary subroutines. Void, string, signed wide values, enums, packed structs, fixed arrays, output/inout/ref and timed automatic tasks reuse the existing call lowering. Calls through typed, generic or forwarded constrained views still execute the actual interface implementation in its own lexical scope and timescale.

The compiler checks task/function kind, return type, argument count, direction, width, signedness, state kind, unpacked dimension lengths (independent of index labels), enum identity and unpacked aggregate identity. Packed vectors, atom types and packed structs match their width/sign/state representation, independent of typedef identity or packed rank. All checks run before generating output. An implementation default must also be declared in the prototype; the values may differ. As observed with VCS W-2024.09, a view supplies its prototype's defaults, while named actuals use the implementation's formal names. Different modports can therefore provide different defaults for the same implementation. Direct instance calls retain the implementation defaults. Defaults that reference interface variables read the actual instance state at the call.

An unused prototype without an interface body is accepted, matching VCS. Calling it is rejected: module-provided exported implementations are not implemented. Modport export, virtual interfaces/classes, interface instance arrays, complete clocking blocks, all SystemVerilog prototype/type syntax and full verification-library compatibility remain gaps. Ordinary backend type/ref restrictions also continue to apply.

[Regression fixtures](../tests/modport_prototypes/regression.py) cover defaults, signature checks, parameter/generate cloning, shared automatic activations, lexical timing and independent dependency partitions. Serial, time-wheel and two-thread runs compare complete ordered per-signal streams; prediction commit/rollback and checkpoint restore reuse those streams. VCS W-2024.09 rejects some prototype-default combinations with `USVSIETD`; these remain explicit reference limitations rather than successful comparisons. VCS reference coverage and release results are recorded in [M144 validation](../validation/m144-modport-prototypes/README.md). No runtime performance result is inferred from these functional tests.
