# Late class specialization binding

SystemVerilog method binding can instantiate a concrete parameterized class after
initial class collection. These types are now registered in their declaration's
lexical scope when lowering a callable. Deferred semantic work is completed
before class layouts and static initializers are lowered. Newly registered base
and nested classes receive static initialization as well; declarations are
protected against duplicate initialization.

Runtime string queries inside functions, including `$bits(string)` and
`$size(string_queue)`, are no longer rejected by the constant-expression
classifier. Integral unary operations on strings retain their explicit diagnostic.

The unchanged Accellera UVM 2020.3.1 library reproduces the original late-class
`map::at` failure. It now reaches `$swrite` without an explicit format string in
`uvm_pool.svh:249`. This remains unsupported: full UVM compilation and `run_test`
are not complete.

Five small fixtures validate specialization identity, static state, factory
singletons, local types and string queries against VCS. They do not independently
reproduce the complete library's late-registration failure. See
`validation/m218-uvm-binding` for the actual full-library reproducer and limits.
