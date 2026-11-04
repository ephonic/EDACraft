# Class output

Display-style `$swrite` now formats class values as object contents. Class `%p`
and `%0p` are supported by `$swrite`, `$sformat`, `$sformatf` and the shared
formatted-value lowering. Output uses the dynamic class layout, including
inherited and static properties in declaration order. A null handle prints
`null`; nested handles print type references, so cycles do not recurse.

Read-only runtime descriptions contain names, field locations, scalar types,
enum labels and container dimensions. Static fields are read from the current
simulation, and object fields from its heap. Descriptions own their data and are
shared immutably by checkpoints; they contain no parser pointers. Metadata is
emitted in stable class-ID order. Each object argument is rendered once at its
evaluation point, preserving the VCS ordering observed with later side effects.

Validated fields include signed numbers, unsigned packed values, four-state
values, enums, reals, strings, nested handles, events, queues, dynamic arrays and
associative arrays. Static containers and multi-dimensional maps are covered.

Class formatting in implicit sensitivity (`always_comb`, `always_latch`, `@*`)
is explicitly rejected: VCS probes do not provide a matching wake-up contract.
Use an explicit event control for this supported path. Fixed-array, struct and
chandle fields currently reject at runtime when printed. Numeric conversions of
class handles and `%p` of non-class values remain unsupported.

Dynamic class formats and literal percent sequences inside object strings have
separate dsim native tests. The VCS W-2024.09 exploratory probes emitted non-UTF8
bytes for dynamic class formats and consumed percent sequences inside object
strings; these probes are retained and excluded from positive VCS alignment.

The complete unchanged public UVM package advances beyond `uvm_pool.svh:249` to
a callback specialization handle assignment at `uvm_callback.svh:607`. Full UVM
compilation and `run_test` remain incomplete.
