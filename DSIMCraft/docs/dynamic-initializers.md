# Dynamic array declaration initialization

M69 supports declaration initialization of one-dimensional integral dynamic arrays:

```systemverilog
integer count = 3;
integer values[] = new[count];
integer resized[] = new[5](values), copy[] = values;

task automatic consume(const ref integer source[], input integer n);
  integer local_values[] = new[n](source), snapshot[] = source;
  integer used = local_values.size();
  // Each call receives independent storage and runs these initializers in order.
endtask
```

Static module/block declarations and locals in elaborated subroutines initialize
before processes start. Explicit static locals shared by specialized call sites
initialize once. Automatic task/function/block locals reset and initialize after
argument copy-in, on each invocation or scope entry. Earlier declarators in the
same ordinary packed/integral declaration are visible to later initializers;
the RTL parser registers them sequentially. Gate parsing remains separate.

Allocation size is evaluated once, followed by a snapshot of the source. Dynamic
and compatible one-dimensional fixed sources copy in declaration order. Copies
are independent. A larger allocation fills its tail with X for four-state elements
or zero for two-state elements; zero-sized arrays stay empty. Signed and wide
integral elements use the existing assignment path. No runtime allocator, event
queue or checkpoint implementation is duplicated.

Static initializer reads/writes, including function storage and side effects, are
included in partition placement. A release regression exercises two independent
workers using real separate kernels. Automatic initialization effects participate
in process dependencies and ordinary prediction/rollback, cancellation and slot
reuse.

Current boundaries:

- M70 adds [equal-width state conversion](array-state-conversion.md) for copies
  and native constructors, with separately recorded VCS constructor differences.
  General element conversion,
  aggregates/enums, multidimensional dynamic storage, assignment patterns, array
  returns remain incomplete. M71 adds
  [fixed-array declaration copies](fixed-initializers.md) from fixed sources.
- Static initializer references to automatic variables are rejected. Ordinary
  scalar static declaration initialization retains its previous constant-only
  restriction; this change does not generalize scalar initialization.
- Static declarations in a subroutine that is never elaborated by a call are not
  executed. Self-referencing declaration initializers are not yet supported by
  symbol binding. Do not infer full IEEE initialization/elaboration coverage.
- Dynamic elements are observed through TRACE/scalar reads, not individually
  declared waveform signals. Previously recorded VCS scheduling/index/resize
  differences still apply.

Validation and the exact shared-source VCS comparison are recorded in
[the M69 evidence](../validation/m69-dynamic-initializers/README.md).
