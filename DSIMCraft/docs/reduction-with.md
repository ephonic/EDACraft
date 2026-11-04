# Array reductions with mapping expressions

The RTL parser and compiler accept `with` on `sum`, `product`, `and`, `or` and
`xor` for the fixed/dynamic integral unpacked arrays supported by M76.

```systemverilog
logic [7:0] a[3] = '{8'hff, 2, 3};
integer total;
initial total = a.sum() with (int'(item)); // 260, using 32-bit mapped values
```

Parentheses are optional. The default iterator is `item`; a single identifier
argument changes its name: `a.sum(x) with (int'(x))`. Each with expression binds
its own read-only iterator. It shadows a same-named outer variable without
changing it. Nested reductions may refer to an outer iterator or shadow it with
a new iterator name. Names do not escape their clause, including in clones of
parameterized modules, generate bodies or automatic subroutine calls.

The mapped expression determines result width and signedness, independently of
the assignment destination. Mapping a predicate to one bit also gives a one-bit
sum, which wraps instead of counting all matches. Cast to an integer width to
count matches. Empty dynamic arrays return zero at the mapped result width;
a singleton retains the mapped raw four-state value. Each element is mapped
once. Packed selects preserve the element's declaration bounds. An out-of-range
select follows the existing four/two-state rules.
Dynamic contents are copied once on entry to the fold.

Expressions support casts, arithmetic, comparisons, conditionals, pure existing
system expressions, one-dimensional packed selects, external scalar/array reads
and nested reductions. External reads join the existing sensitivity and partition
dependencies. Automatic locals and fixed/open value or dynamic const-ref array
arguments, continuous/always_comb expressions, blocking assignments, delayed NBA
sampling and prediction rollback use existing storage and scheduler machinery.
No new runtime or checkpoint state is introduced. The gate parser stays separate.

Current limits:

- Mapping expressions with user function calls or writes/updates are explicitly
  rejected. The iterator cannot be an assignment/ref target.
- One unpacked dimension must remain. Fixed subarray prefixes must be constant.
  Packed multidimensional iterator selects, enum/packed aggregate elements,
  queues, associative arrays, locator/sort methods and result selects remain
  unsupported.
- VCS W-2024.09 binds certain default `item[...]` selections to a same-named
  external variable, while bare `item` resolves to the iterator. dsim uses the
  lexical iterator for both. The original shared input/logs are retained as a
  difference. Aligned fixtures use a named iterator for these selections.
- M76's VCS W-2024.09 dynamic-array implicit-sensitivity difference still applies.
  Shared-source timing alignment uses an explicit scalar refresh dependency.
  Standalone implicit dependency behavior remains checked in the M76 native case.
- Other existing array storage, type and callable binding limits still apply.

See [M77 validation](../validation/m77-reduction-with/README.md) for exact shared
sources, VCS logs, all-bit waveform comparison, replay, sanitizer and release
checks. This addition does not establish complete SystemVerilog/VCS support or
provide a new performance comparison.
