# Dynamic array element nonblocking assignments

M66 adds whole-element immediate, delayed and event-controlled NBA for
one-dimensional integral dynamic arrays, including two-state and wide values.
The RTL and gate parsers remain separate; the implementation extends the compiled
RTL assignment path and existing runtime NBA queues.

```systemverilog
integer a[], index = 0, value = 7;
initial begin
  a = new[2]; a[0] = 0; a[1] = 0;
  a[index] <= #3 value;
  index = 1; value = 9;
  #4; // a[0] == 7: index and RHS were sampled when issued
end
```

Immediate and delayed NBA bind the allocated element at issue. Replacing the
allocation invalidates that pending destination; it cannot write a new array
that later occupies the descriptor or an automatic slot. VCS probes show that
same-length `new[n](self)` retains the pending destination, whereas ordinary
whole-array assignment (including self assignment), resizing and delete/new
replace it. Allocation generations model these cases without keeping pointers
into a mutable vector.

Event-controlled NBA (`<= @event`, `<= @(posedge clock iff guard)` and
`<= repeat(n) @(...)`) samples the RHS/index at issue and resolves current storage
after the event matures. Allocation/resize before the event is supported, including
an initially empty array allocated before delivery. A separate descriptor
invocation identity prevents old pending events from writing a newer invocation
that reuses the same automatic slot. Source/guard expressions retain the existing
restriction against pending references to automatic variables.

Updates enter the existing NBA region after Active/Inactive work. Same-time
updates retain insertion order. Already-issued updates survive cancellation of
the issuing process. Automatic local and input/inout value-formal arrays use their
own storage; an update after return does not retroactively change a prior copyout.
Container identities and pending queue entries participate in checkpoints,
failed-prediction restoration and normal partition dependency analysis.

Known boundaries and measured differences:

- M67 adds [packed element selections](dynamic-selects.md), including native NBA
  extensions that VCS W-2024.09 rejects as NYI. Packed aggregate member selection
  and whole-array timed/NBA remain unsupported. M68 adds
  [concatenated dynamic targets](dynamic-concat.md), retaining the measured
  index-function and allocation-resize compatibility boundaries.
- Unknown/out-of-range immediate/delayed NBA indices raise a runtime diagnostic
  at issue. Event-controlled destinations are checked when the event delivers.
  VCS probes also reject the three tested immediate/delayed invalid-index cases;
  exact diagnostic wording is not claimed identical.
- Writable ref array NBA works in dsim's separately tested native path. VCS
  W-2024.09 rejects the tested ref-port delayed NBA with NYI; that extension is
  excluded from the six shared-source alignment models. Const ref remains readonly.
- In a separate delayed-NBA index-function probe, VCS calls the function twice
  while dsim calls it once. This difference is retained explicitly; the probe is
  not counted as aligned. Shared-source alignment models use ordinary indices.
- Functions retain the existing zero-time blocking-statement restriction.
- Dynamic waveform element declarations, dynamic element scalar-ref arguments,
  multidimensional dynamic containers and broader array conversions remain
  future work. Shared scalar observations and TRACE values do not constitute
  a dump of all dynamically allocated bits.

Validation: [M66 evidence](../validation/m66-dynamic-nba/README.md).
