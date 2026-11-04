# Unpacked struct storage state (M92)

A `bit` member of an unpacked struct has its own two-state representation. After
`s.bits += 8'bx`, the stored member is zero; comparing the complete struct with a
zero-valued instance must return true. Previously the member read converted X/Z,
but selected, concatenated and compound writes could leave unknown bits in the
flattened storage, making whole-struct equality return X or false.

The compiler now derives a physical mask from each unpacked struct declaration.
The runtime clears unknown bits only under that mask when committing a store,
before change detection, event notifications and waveform capture. This applies
to direct and selected writes, variable-index fixed array elements, concatenations,
compound updates, blocking intra-assignment delays, immediate/delayed/event NBA,
whole-struct assignment patterns, function results and task output/ref arguments.
Nested unpacked members and fields wider than 64 bits retain their own state type.
Automatic activation copies and prediction checkpoints carry the mask metadata.

Mixed packed struct/union members continue to share their containing four-state
representation: writing X/Z through a packed bit view retains those raw bits, and
reading that view converts them. A mixed packed member nested inside an unpacked
struct retains this behavior. See [packed storage](packed-storage.md).

Declaration defaults and masks are remapped along with signal IDs during port
collapsing. Subroutine integral struct locals, formals and results receive the
same metadata, including default initialization on each automatic activation.
Designs without a masked unpacked struct do not enable the mixed-state runtime
feature or add its signal metadata/commit branch.

Run:

```sh
python3 tests/unpacked_state/regression.py build/dsim /tmp/unpacked-state
```

The four models check explicit RTL value oracles, 52 waveform captures across
serial/time-wheel/threads, four failed prediction replays, two actual partitions
and an independent packed-storage control. Same-source VCS W-2024.09 comparison
checks exact TRACE output and all 728 common physical bits after settling, with
explicit mappings for VCS's member declarations. The 64 array bits that VCS does not dump are listed separately in the evidence;
private automatic storage is excluded from both exported traces.

This extends the existing fixed integral unpacked struct subset. It does not
implement strings, dynamic containers or unpacked array members inside structs,
classes, arbitrary hierarchy writes or complete SystemVerilog aggregate semantics.
No new performance claim is made. Evidence: [M92](../validation/m92-unpacked-state/README.md).
