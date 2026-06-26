# int_div

## Parameters
- `IDLE = 3'b000`
- `PRE = 3'b001`
- `COMPUTE = 3'b010`
- `RECOVERY = 3'b011`
- `FINISH = 3'b100`

## Ports (11)
- `input [1] clk`
- `input [1] rst_n`
- `input [`XLEN-1:0] a_i`
- `input [`XLEN-1:0] d_i`
- `input [1] sign_bit`
- `input [1] in_valid_i`
- `input [1] out_ready_i`
- `output [1] in_ready_o`
- `output [1] out_valid_o`
- `output [`XLEN-1:0] q_o`
- `output [`XLEN-1:0] r_o`

## Logic Block Types
- comb
- seq_async_reset
