# SystemVerilog assignment patterns

The RTL parser keeps `'{...}` separate from concatenations. The compiler expands
patterns using the destination layout, then emits existing packed expressions or
fixed-array snapshots. The gate-netlist parser and simulator scheduler are unchanged.

```systemverilog
integer samples[2:0] = '{1, 2, 3};
logic [1:0][7:0] lanes;
typedef struct packed { bit [3:0] tag; logic [7:0] data; } packet_t;
packet_t packet;
initial begin
  samples = '{0: 8, default: 4}; // samples[2]=4, [1]=4, [0]=8
  lanes <= #2 '{8'ha5, 8'hc3};
  packet = '{data: 8'h80, tag: 4'hf};
end
```

Supported patterns:

- Positional entries in declaration order, `default` fill, numeric index keys
  (including negative packed indices), and packed struct member names.
- Nested patterns for multidimensional fixed unpacked arrays, packed arrays and
  packed structs. Unpacked patterns require a nested pattern at each dimension.
- Constant repetition, such as `'{3{9}}` and `'{2{'{2{11}}}}`.
- Fixed-array declaration initialization, including automatic task/function
  locals, blocking/NBA assignments and constant or runtime intra-assignment delays.
- Packed declaration initialization, blocking/NBA and event/delay assignments,
  function-result assignments by name, and continuous packed assignments.

Each packed element/member is sized in its own destination context. Signed
extension, four-state values, bit conversion and enum identity use the existing
type and storage rules. A mixed bit/logic packed struct preserves raw X/Z in its
shared storage, including bit fields; reading a bit member converts X/Z to zero.
An entirely two-state aggregate converts at storage, matching existing aggregate
semantics and VCS. Duplicate keys/defaults, missing entries without default,
out-of-range indices, excess entries and mixed positional/keyed entries fail
before code emission.

Fixed-array RHS values are all sampled before destination stores. Delayed NBA
also captures a dynamic destination prefix at statement execution. Blocking
intra-assignment delay preserves the RHS snapshot and samples the target prefix
when the process resumes, matching the existing fixed-array copy implementation.
Buffers belong to the existing process/activation state, so prediction rollback
and parallel placement use the existing checkpoint and dependency mechanisms.

Current boundaries:

- Untyped patterns require one of the supported assignment contexts above.
  Typed patterns (`T'{...}`), type keys, parameter/expression index keys, direct
  pattern call arguments/return expressions, dynamic arrays and associative
  containers remain unsupported.
- Index keys/counts must be known integral constants represented in at most
  32 bits. Counts must be positive; expanded lists contain at most 1,048,576
  entries. Existing array, packed-width and nonnegative unpacked-bound limits apply.
- Pattern value expressions must have no persistent side effects, procedural-only
  operations or selection checks. Simple variable reads and pure arithmetic work.
- Patterns cannot construct enums from raw bits or packed unions with overlapping
  members. Enum members in a struct require a value of the same enum type.
- Existing restrictions on net arrays, automatic NBA targets, whole-array event
  controls and constant scalar declaration initializers still apply.

Acceptance includes shared sources run on VCS W-2024.09, three native scheduler
backends, ordered/settled VCD and DWF identity, failed-prediction replay, actual
independent worker partitions and ASan/UBSan. See
[M74 validation](../validation/m74-assignment-patterns/README.md) for exact scope.
