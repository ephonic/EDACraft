# RTL module and primitive instance arrays

The RTL front end expands one-dimensional fixed instance ranges into independent
module scopes. This includes parameterized bounds, ascending/descending ranges,
negative bounds and instances inside generate blocks. Each module element has its
own signals, process state, local arrays, subroutine specializations and explicit
static locals. Waveform scopes include the declared index, such as `top.u[-1]`.
The compact gate-netlist parser remains separate and unchanged.

```systemverilog
module lane(input wire clk, input wire [3:0] seed, output logic [3:0] q);
  initial q = 0;
  always @(posedge clk) q <= #1 q + seed;
endmodule
module testbench;
  logic [2:0] clk;
  logic [11:0] seed;
  wire [11:0] q;
  lane u[2:0](clk, seed, q);
endmodule
```

A packed terminal whose width equals one formal port broadcasts to every element.
A terminal whose width equals the formal width times the instance count splits in
instance declaration order: the leftmost declared instance receives the most
significant part, regardless of index direction. Other widths are rejected.
Both positional and named module connections use this rule. Static output slices
can cross concatenation boundaries. Existing net bit links preserve electrical
connectivity for input/inout ports; output concatenations retain their existing
directional adapter behavior. Variable outputs use existing writer checks and
state conversion, so overlapping independent drivers are still rejected.

RTL `and/nand/or/nor/xor/xnor`, `buf/not`, and `bufif0/bufif1/notif0/notif1`
instance arrays apply the same rule with scalar primitive terminals. Scalar
inputs/enables broadcast; a vector terminal splits into one bit per primitive.
Existing four-state evaluation, drive resolution, and constant rise/fall/turn-off
delays are reused. Each delayed primitive remains an independent scalar channel.

Expansion adds no scheduler or checkpoint state. NBA, timed wakeups, waveform
transactions, prediction rollback and automatic partition placement operate on
the ordinary independent elements. Whole-port broadcasts may collapse nets;
vector connections use static slices and existing bit links/drivers.

Current boundaries:

- One fixed range per instance, signed 32-bit known constant bounds and at most
  65,536 elements per array; existing packed width limits also apply.
- Unpacked module ports in instance arrays are rejected. Multidimensional instance
  arrays, full hierarchical expression access and interface arrays remain absent.
- Output/inout terminal selections must be static. Terminal expressions that
  mutate persistent state or emit selection diagnostics are rejected rather than
  silently multiplying side effects across expanded adapters.
- Multi-output `buf/not`, UDP, general strength modeling and other previous
  primitive limitations are unchanged. This is RTL support; the compact gate
  parser does not inherit it automatically.

Run `ctest --test-dir build -R '^rtl_instance_arrays$' --output-on-failure`.
Shared sources and comparison details are in
[the M73 validation](../validation/m73-instance-arrays/README.md).
