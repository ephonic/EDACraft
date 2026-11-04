# Class compatibility before layout registration

A concrete parameterized class can be created while binding a method body,
after initial runtime layout collection. Its inheritance is already known to
the parser. Assignment checking now remembers semantic class identities and
walks this inheritance graph directly, independently of runtime layout
registration. A legal upcast no longer fails just because its source type has
no registered layout yet.

Class identity remains nominal: different parameterizations and unrelated
classes do not become assignment-compatible. Implicit downcasts are rejected;
`$cast` keeps its runtime checks. `ref` and `const ref` still require identical
class types. Invalid assignments now include source and destination type names
where available. Allocations and static initialization keep the existing explicit
layout registration path; a type query does not allocate or initialize a class.

The unchanged Accellera UVM 2020.3.1 library reproduces the original failure in
`uvm_callback.svh:607`, assigning a newly specialized callback to its typed base.
It now reaches `uvm_reg_item.svh:281`, where a class member dynamic array is passed
to a `ref` formal. That heap-backed array alias is still unsupported. Full UVM
compilation and `run_test` remain incomplete.
