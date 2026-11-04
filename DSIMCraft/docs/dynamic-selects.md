# Dynamic array element packed selects

One-dimensional integral dynamic array elements support `a[i][bit]`,
`a[i][msb:lsb]`, `a[i][base+:width]` and `a[i][base-:width]` reads and procedural
updates. Constant ranges must be within the descending packed declaration;
indexed widths must be positive constants. Two-state and wide four-state
elements, automatic locals, dynamic value formals, ref/const-ref formals,
increment/decrement and compound updates use the existing element storage.
Const-ref destinations remain readonly.

Blocking updates merge only selected bits. Intra-assignment delay/event controls
capture the RHS before waiting and evaluate both the array and packed indices
after the wait. Compound updates capture both addresses once. Array descriptor
dependencies include both indices and participate in partitioning.

Immediate, delayed and event-controlled element NBA can also update a packed
selection. Both indices and RHS are captured when issued. The selected bits merge
with the element at **commit**, preserving other writes to disjoint bits. Ordinary
and delayed NBA retain the allocation generation; event NBA retain the descriptor
invocation and resolve its current storage when delivered. The existing NBA,
delay and event queues own these targets and restore them with checkpoints.
Whole-element blocking updates retain their direct store path.

VCS W-2024.09 accepts the shared blocking models, but rejects the tested packed
dynamic-element NBA with `NYI: Non-blocking assignment with bit/part select on
dynamic type`. NBA support is therefore validated as a dsim extension. A separate
configuration replaces dynamic declarations with fixed arrays to compare common
NBA bit-update behavior against VCS; this is **not** a dynamic-array VCS alignment
claim. Allocation replacement and event-time storage are additionally checked by
the native timing model and kernel tests.

Known limits and differences:

- M68 adds [concatenated dynamic destinations](dynamic-concat.md). Element
  scalar-ref binding, packed aggregate member selection, ascending declarations and multidimensional dynamic arrays
  remain unsupported. Whole-array timed/NBA assignments remain unsupported.
- Unknown or fully out-of-range packed indices read X (converted to zero for
  two-state elements) and write nothing. Indexed selects with partial overlap use
  the existing dsim clipping policy and preserve the RHS bit offset. An independent
  probe records that VCS ignores writes crossing the negative lower bound for both
  fixed and dynamic arrays, whereas dsim writes the overlapping bits for the
  tested nonnegative index. Signed-negative packed indices retain the existing
  unsupported boundary. This difference is excluded from alignment claims, with
  full raw traces retained separately.
- M66's index-function evaluation difference and ref-port NBA NYI remain recorded.
  No dynamic-element waveform declarations are added: scalar reads and TRACE
  values observe contents, and comparison covers every exported physical bit.

Tests: `tests/dynamic_selects`, the three `dynamic_nba` kernel variants and
[M67 evidence](../validation/m67-dynamic-selects/README.md).
