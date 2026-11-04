# Dynamic arrays

M64 adds runtime storage for one-dimensional unpacked dynamic arrays of integral
values, including packed vectors, signed values, two/four-state elements and wide
values. The RTL parser remains independent of the gate parser.

```systemverilog
integer values[], copy[];
initial begin
  values = new[3];
  foreach (values[i]) values[i] = i + 1;
  copy = values;                 // independent element values
  values = new[5](values);        // preserve prefix, default-initialize the tail
  copy.delete();
  $display("%0d", values.size()); // 5
end
```

Supported paths:

- Empty initial storage; runtime `new[n]`, `new[n](array)`, zero length,
  grow/shrink/self-resize, whole dynamic-array copy and `delete()`.
- A compatible fixed one-dimensional source is copied in declaration order.
  The destination adopts the source length on ordinary whole-array assignment.
- Element blocking reads/writes, increment/decrement and compound updates;
  dynamic index side effects are evaluated once for updates. Invalid reads return
  the element's default value; invalid writes still evaluate the RHS and do not
  modify storage.
- `size()`, `$bits`, `$dimensions`, `$unpacked_dimensions`, `$size`, `$left`,
  `$right`, `$low`, `$high`, `$increment`, including runtime dimension arguments.
  An empty dynamic dimension has left/low 0, right/high -1, size 0, increment -1.
- One unpacked `foreach` index, break/continue; automatic task/function/block
  locals, repeated calls, suspended tasks, fork lifetime and cancellation.
- Dynamic contents and length participate in ordinary checkpoints and failed
  predictions. Reads/writes use the array descriptor in dependency analysis and
  partition placement. Independent arrays can execute in separate kernels.

Storage belongs to `Sim`, indexed by the physical descriptor signal. Checkpoints
copy container values as part of kernel state. Automatic activation slots keep
independent descriptors and clear reused storage. Functions also clear automatic
containers on entry when using the existing non-reentrant compiled call template.
No maximum runtime length is baked into generated element slots. The allocation
limit is 1,048,576 elements; unknown, negative or excessive lengths raise a runtime
diagnostic. This allocation diagnostic policy is not claimed identical to VCS.

Current limits:

- M65 adds [dynamic array formals and references](dynamic-arguments.md) for
  automatic subroutines. Dynamic element references remain unsupported. M63's
  `[]` value formals still specialize **fixed** actuals by call site.
- No multidimensional/ragged dynamic containers, array returns,
  assignment patterns, packed aggregate member selects,
  whole-array timed/NBA assignment, dynamic `$readmem*`, or dynamic `inside` sets.
- M70 adds [equal-width packed integral state conversion](array-state-conversion.md).
  Ordinary copies check signedness, atomic base kind and enum/aggregate identity.
  Broader conversions remain future work; constructor differences with VCS are
  recorded separately.
- `foreach` currently accepts one nonempty unpacked index. Resizing the iterated
  array within the body is not part of the VCS alignment coverage.
- Waveform capture currently exposes scalar observations and fixed storage;
  dynamic length/element declarations are not yet exported. Internal descriptor
  notification tokens are hidden. Verification compares all exported physical
  bits and explicitly observes dynamic contents through shared SV scalar reads
  and TRACE checks; it does not claim a dump of every allocated dynamic bit.

M66 adds [dynamic element NBA](dynamic-nba.md), including delay/event controls.
M67 adds [element packed selects](dynamic-selects.md), including procedural
updates and separately validated NBA extensions.
M68 adds [mixed concatenation targets](dynamic-concat.md) with queued NBA updates.
M69 adds [dynamic declaration initialization](dynamic-initializers.md).

Validation: [M64 evidence](../validation/m64-dynamic-arrays/README.md).
