# Concatenation targets with dynamic array elements

Procedural concatenation assignments may mix integral dynamic array elements,
their packed selections, ordinary variables and fixed-array elements. Nested
concatenations use the existing flattening and RHS width rules. Reads and writes
retain the array descriptor dependencies, including every element/packed index.
The RTL and gate parsers remain separate; this change uses the existing RTL AST.

The RHS is captured once. All LHS addresses are then evaluated left to right
before any destination is written. Writes apply left to right, so the rightmost
piece wins when targets overlap. Invalid blocking element/packed destinations
skip that piece while valid pieces still update. Const-ref and net protections
apply to every piece. Two-state conversion occurs per destination.

Blocking intra-assignment delay/event controls capture the RHS before waiting,
then evaluate all addresses on resumption. Immediate, delayed and event NBA
enqueue a single parts update with captured indices and RHS. An automatic scalar
or fixed-array NBA destination is rejected even when another piece is a dynamic
element; automatic dynamic elements retain their existing M66 support.

Normal/delayed dynamic targets retain the allocation generation, with the same
same-length `new[n](self)` exception as M66. Event targets retain the descriptor
invocation and resolve current storage when delivered. An invalid immediate or
delayed dynamic element raises a runtime error at issue; blocking invalid pieces
are no-ops. Mixed scalar destinations remain live if allocation replacement
invalidates only their dynamic neighbor. Checkpoints copy the entire queued update.
No new scheduling queue is introduced. Single-element fast paths are retained.

Real VCS W-2024.09 probes and boundaries:

- Whole-element delayed/event concatenations and blocking packed/mixed targets
  are compared using unmodified shared sources and every exported physical bit.
- VCS reports an internal compiler SIGSEGV for the tested packed dynamic-element
  concatenation NBA; M67's single-target packed NBA reports NYI. This native extension
  has a separately compiled fixed-array reference configuration; its result is
  not counted as dynamic-array VCS alignment.
- In the independent function-index probe, blocking evaluation agrees (`912`),
  while NBA observes VCS `11229` versus dsim `912`. This preserves M66's measured
  repeated-index-evaluation difference.
- A separate `growth-after-event` sequence preserves a pending target across a
  particular self-initialized growth in VCS, while dsim drops it by allocation
  generation. An independent direct 2-to-4 growth drops targets on both tools.
  No general VCS storage-capacity rule is inferred from these observations.
  Both raw sources and traces are retained as an explicit compatibility boundary.
- M67's lower-bound clipping difference and signed-negative/ascending select
  limits remain. Whole-array timed/NBA assignments, dynamic element scalar-ref
  binding, multidimensional dynamic containers and aggregate element members
  remain unsupported. Dynamic waveform element declarations are not added.

Validation: `tests/dynamic_concat`, the three `dynamic_nba` kernel variants and
[M68 evidence](../validation/m68-dynamic-concat/README.md).
