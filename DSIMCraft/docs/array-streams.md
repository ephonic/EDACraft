M233 adds dynamic-array/queue streaming assignment targets, mixed static/dynamic targets and VCS-checked partial-element allocation/bit order. See [M233 validation](../validation/m233-stream-targets/README.md). Earlier target limitations below describe M230.

# Runtime array streams and bit-stream casts

M230 supports runtime-sized integral queues/dynamic arrays as stream operands,
nested streams, slice reversal, mixed packed/array operands, packed destinations
and fixed/dynamic/queue destination casts. Source operands are evaluated once
from left to right. Four-state bits are retained until a two-state destination
or cast converts X/Z to zero. Packed/fixed stream destinations pad on the right;
plain bit-stream casts require matching size. Bounded queue casts retain capacity.
The temporary stream is limited to 1048576 bits. Existing fixed-width packed
streams keep their previous generated path.

Fixed string arrays now have string storage for each element, including module
and automatic locals, dynamic index reads/writes, whole copies and fixed array
input/ref formals. Automatic frames initialize elements to empty strings and
retain them across suspension and rollback. Dynamic string arrays, string ports,
class fixed-array properties and timed/NBA string element stores remain limited.

The unchanged UVM register-map stream conversion now compiles. Its fixed local
string array in the bit-bash sequence also compiles. Complete UVM still stops at
uvm_phase.svh:2092, where a task passes an associative array by value/output;
whole-map ref/const-ref transfers are supported separately. No complete UVM
native model or run_test success is claimed.

Twelve of fourteen same-byte VCS fixture outputs match. Two explicit differences
remain: VCS preserves order in the tested bare-byte-queue left stream with an
8-bit slice; dsim applies slice reversal. In a mixed stream with a later scalar
side effect, dsim snapshots the earlier array operand before that effect, whereas
the tested VCS result reads its modified value. These probes are not counted as
alignment passes. An auxiliary string array out-of-range method query also differs:
dsim reads an empty string; VCS rejects the tested access. See
[M230 evidence](../validation/m230-array-streams/README.md).
