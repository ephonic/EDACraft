# Array value state conversion

M70 supports equal-width packed integral element conversion between four-state
`logic/reg` and two-state `bit` for dynamic whole-array copies, declaration
initializers and fixed/dynamic `input/output/inout` array value arguments.
X and Z bits become zero when copied to two-state storage. Copying back retains
those known values; source arrays remain independent. Signedness, atomic base
kind, enum/aggregate identity, rank and fixed dimension sizes still must match.
`ref/const ref` continue to require exact element equivalence, including state
representation, because they alias storage rather than convert values.

```systemverilog
logic [7:0] source[] = new[2];
bit [7:0] saved[] = source;
task automatic update(inout bit [7:0] values[]);
  values[0]++;
endtask
initial begin
  source[0] = 8'b1xz001zx;
  saved = source;             // saved[0] is 8'h84
  update(source);             // copy-in converts; copyout makes source[0] 8'h85
end
```

The implementation reuses existing per-element assignment and dynamic storage
replacement. Four-state destinations retain X/Z values from four-state sources;
two-state destinations clear unknown bits. Fixed actuals, descending ranges and
runtime-selected subarrays use the existing declaration-order value transfers.
Automatic frames, cancellation, partition dependencies and checkpoints keep the
same storage and scheduling paths. The RTL and gate parsers remain independent.

Equal-width `new[n](source)` also converts each copied element in dsim, including
fixed sources and integral atomic sources. The destination default fills any
uncopied tail. This path is **not claimed as shared-source VCS alignment**:
installed VCS W-2024.09 accepts cross-state constructors but the repeated probes
show different element values from ordinary element-wise conversion, for 8-,
32- and 96-bit sources. Raw runs are retained. A separate
`ELEMENTWISE_REFERENCE` configuration replaces constructors with allocation and
explicit scalar assignments to check the intended native behavior. No universal
rule about VCS allocation or memory layout is inferred from these observations.

Width-changing constructors/copies, conversions between distinct atomic kinds
for ordinary array copies or value formals, signedness changes for copies/value formals, multidimensional
dynamic containers, array returns, assignment patterns, dynamic element scalar
ref binding and dynamic element waveform declarations remain incomplete. Other
previously recorded VCS differences remain. No new performance result is claimed.

Run `ctest --test-dir build -R '^rtl_array_state_conversion$' --output-on-failure`.
Evidence: [M70](../validation/m70-array-state-conversion/README.md).
