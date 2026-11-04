# Packed runtime selects

The RTL compiler supports reading and procedurally assigning `data[index]`,
`data[index +: WIDTH]`, and `data[index -: WIDTH]`. `WIDTH` is a positive
elaboration-time constant (including parameter arithmetic), at most 1,048,576.
Descending declarations with nonzero lower bounds and values wider than 64 bits
are supported. Index expressions participate in sensitivity and parallel-domain
dependencies. Variable selects used as module input expressions are directional
adapters; output/inout actuals and continuous assignment destinations must still
use static targets. The gate netlist parser remains separate and unchanged.

For bit/indexed selects, an X/Z index reads X and writes nothing. Fully out-of-range selects have the
same behavior. Partially overlapping selects return X for unavailable bits and
write only overlapping bits, using the corresponding RHS offsets. Known high
words in a wide index are checked instead of silently truncating to 64 bits.

Nonblocking assignments, including delayed NBAs, capture the destination index
and RHS when issued. Blocking intra-assignment delay captures the RHS at entry
and evaluates the destination after the wait. Pending targets survive checkpoint
restore and rejected prediction replay. Concatenation destinations retain the
existing left-to-right application order: the rightmost overlapping piece wins.

Signed runtime indices now retain their sign in bit/indexed part reads and
stores, including clipped negative positions and descending declarations with
negative lower bounds. Unknown indices and positive/negative values outside the
supported range remain invalid. Wide signed indices must fit a signed 64-bit
position; non-sign-extension high words are rejected. This also applies to
packed member views, compound updates, delayed NBAs and concatenated stores.

Ordinary `[msb:lsb]` bounds must both be constant and in range. Later parser
milestones added packed dimensions and ascending declaration support; this
single-dimension indexed-select change does not imply dynamic output/inout
adapters or complete multidimensional partial clipping.

Actual VCS probing confirmed the NBA and blocking-delay sampling rules above.
A separate `large_index.sv` probe retains a discovered difference: with a 128-bit
index containing a nonzero high word, VCS selected effective in-range bits in
some operations, while dsim treated the full value as out of range. This edge
case is tracked separately from the common-range VCS equivalence tests.
