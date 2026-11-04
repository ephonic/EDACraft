# SystemVerilog streaming concatenations

The RTL parser represents streams separately from shifts and replication. The
compiler lowers them to owned packed expressions and existing destination parts.
The gate parser, scheduler state and checkpoint format are unchanged.

```systemverilog
logic [7:0] bytes[2:0] = '{8'h12, 8'h34, 8'h56};
logic [23:0] packed_value;
logic [7:0] output_bytes[0:2];
initial begin
  packed_value = {<<8{bytes}};       // 24'h563412
  {>>{output_bytes}} = packed_value;
end
```

Supported:

- Both directions, default one-bit slices, positive constant slice sizes
  (1..1,048,576), integral built-in type sizes and fixed integral typedef sizes.
- Multiple and nested packed operands, fixed unpacked arrays and subarrays with
  static prefixes. Elements follow declaration order, including descending and
  multidimensional arrays. Packed values retain their raw four-state bits.
- Declaration initialization, constants/parameters, continuous packed RHS,
  procedural blocking/NBA, fixed delays, automatic locals, scalar value arguments
  and function returns. Function operands are evaluated once per stream.
- Top-level streaming targets made of static packed storage, static selects and
  fixed unpacked arrays/subarrays. Assignment uses existing simultaneous-value
  snapshots, automatic-variable checks and readonly checks.

A left stream reverses slice order while preserving bit order within slices.
A short most-significant slice participates in the reversal; for example
`{<<4{10'b1011001101}}` is `10'b1101110010`. Right streaming keeps bit order.
Streaming expressions are unsigned and self-sized. Direct packing requires a
destination at least as large as the source and zero-pads on the **right**:
`logic[23:0] x = {<<8{16'h1234}}` gives `24'h341200`.
Unpacking requires a source at least as large as the destination. It takes the
most-significant destination-width bits, then applies the target's stream order.
This distinction matters for partial slices: `{<<4{ten_bits}} = 16'habcd` gives
`10'b1111101010`, rather than applying an inverse bit permutation.

Current boundaries:

- Dynamic/associative containers, queues, strings, `with` ranges, dynamic array
  prefixes on source or target, dynamic target selects, nested streaming targets
  and direct raw streaming targets of enum type remain unsupported.
- Direct streaming module connections and port defaults require a packed
  temporary first.
- Assigning to a whole unpacked array requires an explicit streaming target as
  above. Existing fixed-array port, width and storage limits continue to apply.
- A direct stream RHS with an intra-assignment event control is explicitly
  rejected; first capture the stream in a packed temporary, then use that value
  with the event control. VCS W-2024.09 exhibits different control/update behavior
  for the direct stream and ordinary packed RHS in the retained probe. This
  combination is not claimed as aligned.
- The subset does not establish complete bit-stream cast or SystemVerilog
  verification support. Unsupported source syntax still fails at compilation.

Narrow streams use one pair of 64-bit masks without heap allocation. Wider
streams move runs across source/destination word boundaries into one output word
vector. No performance comparison with VCS is claimed by this change.

See [M75 validation](../validation/m75-streaming/README.md) for accepted fixtures,
VCS evidence, waveform identity, replay and stable-release results.
