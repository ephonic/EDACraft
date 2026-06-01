# array_multiplier

## Parameters
- `LATENCY = 2`

## Ports (22)
- `input [1] clk`
- `input [1] rst_n`
- `input [`NUM_THREAD-1:0] mask_i`
- `input [`XLEN-1:0] a_i`
- `input [`XLEN-1:0] b_i`
- `input [`XLEN-1:0] c_i`
- `input [5:0] ctrl_alu_fn_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] ctrl_reg_idxw_i`
- `input [`DEPTH_WARP-1:0] ctrl_wid_i`
- `input [1] ctrl_wvd_i`
- `input [1] ctrl_wxd_i`
- `input [1] in_valid_i`
- `input [1] out_ready_i`
- `output [1] in_ready_o`
- `output [1] out_valid_o`
- `output [`NUM_THREAD-1:0] mask_o`
- `output [5:0] ctrl_alu_fn_o`
- `output [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] ctrl_reg_idxw_o`
- `output [`DEPTH_WARP-1:0] ctrl_wid_o`
- `output [1] ctrl_wvd_o`
- `output [1] ctrl_wxd_o`
- `output [`XLEN-1:0] result_o`

## Submodule Instances
- `U_mul`

## Logic Block Types
- seq_async_reset
