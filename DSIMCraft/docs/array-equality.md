# Unpacked array equality and bounded elaboration

The RTL compiler supports `==`, `!=`, `===`, and `!==` on equivalent unpacked
array values: queues, dynamic arrays, and fixed arrays/subarrays. Operands must
have equivalent element types and matching container kinds/ranks; fixed axes
must have matching lengths. Bounds may differ in direction and origin. A queue
and a dynamic array are not equivalent types, even with matching elements.

Operands are captured once before comparison. Length mismatch is false for
both equality operators. Ordinary equality preserves X/Z uncertainty unless a
known differing element decides the result; case equality compares all four
states exactly. Strings compare contents, class handles compare identity, and
supported unpacked structs retain their string fields. There is no object deep
comparison. Real arrays, associative arrays and compact fixed-array whole-value
operations remain explicit limitations.

Direct array comparison event operands sample at every container change, so a
transient result in one process activation is not lost. Woken processes retain
normal Active scheduling. Pending NBA event controls on these comparisons are
explicitly rejected. Predicted event observations and container contents are
restored on rollback.

String `foreach` uses the current string length on each iteration, including
class properties and automatic function inputs. Character reads on string
properties follow the string indexing path. Queue methods accept a contextual
struct assignment pattern. `$sformat` and `$swrite` with an explicit string
format are permitted in functions; formatting has no implicit newline. Bare
numeric/multiple-format `$swrite` argument lists are not implemented.

For serial RTL, a generated call body exceeding 1 MiB triggers one fresh lowering
using the existing shared-function backend. This bounds repeated function-body
expansion without depending on a design or library name. An explicit
`--shared-functions` avoids the first attempt. Parallel or gate-assisted
lowering does not automatically switch backends; exceeding the budget produces
a diagnostic. This is not a general bound on all compiler memory usage.

Repeated equivalent signal registrations are emitted as a loop, preserving IDs,
order and per-element storage. This addresses native compiler growth for SRAM
models without selecting a compact storage mode or dropping wave metadata.
Large waveform declaration generation remains a separate scaling concern.

`tests/array_equality` checks native executions in default/shared/time-wheel
modes against exact-source VCS traces, full decoded waveforms, a failed prediction
replay, output protection and an exponential call graph. See
`validation/m216-gap11` for REPORT-GAP11 reproduction and release evidence.
