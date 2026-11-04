# Unpacked array reductions

The RTL parser and compiler support `sum`, `product`, `and`, `or` and `xor`
on one-dimensional fixed or dynamic unpacked arrays of packed integral elements.
Empty parentheses are optional. A multidimensional fixed array can select a
subarray using constant indices before calling a reduction.

```systemverilog
logic [7:0] data[3] = '{8'hff, 2, 3};
integer result;
initial result = data.sum(); // 4: reduction uses 8-bit arithmetic
```

The result retains the element's width and signedness. Assignment context does
not widen intermediate arithmetic. A singleton preserves raw X/Z bits for all
five methods. An empty dynamic array returns element-width zero for all five
methods, including `product` and `and`. These rules were checked against VCS
W-2024.09, with the shared fixtures and raw logs retained in
[M76 validation](../validation/m76-array-reductions/README.md).

Supported uses include declarations, continuous expressions, `always_comb`,
blocking assignments, NBA/delayed RHS sampling, automatic locals and fixed/open
value arguments or dynamic `const ref` arguments. Fixed-array elements and
dynamic-array descriptors contribute read dependencies. Dynamic contents are
sampled into an owned vector for each reduction. Existing array storage and
checkpoint machinery provide prediction rollback; no new runtime state is added.
Fixed reductions emit an inline fold using the existing four-state operations.
VCS W-2024.09 did not reevaluate the retained dynamic-only `always_comb` probe
after element writes, resize or delete. dsim tracks these changes. Shared-source
waveform alignment uses an explicit refresh dependency; the original probe is
retained and checked separately against dsim expectations. This difference is
not counted as an aligned VCS feature.
The gate parser remains separate.

Locator/sort methods, queues, associative arrays, enum or
packed aggregate elements, whole multidimensional reductions, runtime subarray
indices and selecting/assigning a method result remain unsupported. Dynamic
arrays and unsized value formals retain their existing binding rules; a dynamic
`const ref` formal requires a dynamic actual of the same type. These additions
do not establish complete SystemVerilog verification or VCS compatibility, and
no new performance comparison is claimed.

M77 adds [with mapping expressions](reduction-with.md), including default/named
lexical iterators, casts, predicates, nested reductions and external read
dependencies. The linked description defines the current restrictions.
