# fpmv

## Parameters
- `EXPWIDTH = 8`
- `PRECISION = 24`
- `SOFT_THREAD = 4`

## Ports (21)
- `input [1] clk`
- `input [1] rst_n`
- `input [2:0] op_i`
- `input [EXPWIDTH+PRECISION-1:0] a_i`
- `input [EXPWIDTH+PRECISION-1:0] b_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] ctrl_regindex_i`
- `input [`DEPTH_WARP-1:0] ctrl_warpid_i`
- `input [SOFT_THREAD-1:0] ctrl_vecmask_i`
- `input [1] ctrl_wvd_i`
- `input [1] ctrl_wxd_i`
- `input [1] in_valid_i`
- `input [1] out_ready_i`
- `output [1] in_ready_o`
- `output [1] out_valid_o`
- `output [EXPWIDTH+PRECISION-1:0] result_o`
- `output [4:0] fflags_o`
- `output [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] ctrl_regindex_o`
- `output [`DEPTH_WARP-1:0] ctrl_warpid_o`
- `output [SOFT_THREAD-1:0] ctrl_vecmask_o`
- `output [1] ctrl_wvd_o`
- `output [1] ctrl_wxd_o`

## Logic Block Types
- comb
- seq_async_reset
