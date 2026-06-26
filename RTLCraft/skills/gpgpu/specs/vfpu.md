# vfpu

## Parameters
- `EXPWIDTH = 8`
- `PRECISION = 24`
- `LEN = EXPWIDTH + PRECISION`
- `SOFT_THREAD = 4`
- `HARD_THREAD = 4`

## Ports (23)
- `input [1] clk`
- `input [1] rst_n`
- `input [SOFT_THREAD*6-1:0] op_i`
- `input [SOFT_THREAD*3-1:0] rm_i`
- `input [SOFT_THREAD*LEN-1:0] a_i`
- `input [SOFT_THREAD*LEN-1:0] b_i`
- `input [SOFT_THREAD*LEN-1:0] c_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] ctrl_regindex_i`
- `input [`DEPTH_WARP-1:0] ctrl_warpid_i`
- `input [SOFT_THREAD-1:0] ctrl_vecmask_i`
- `input [1] ctrl_wvd_i`
- `input [1] ctrl_wxd_i`
- `input [1] in_valid_i`
- `input [1] out_ready_i`
- `output [1] in_ready_o`
- `output [1] out_valid_o`
- `output [SOFT_THREAD*64-1:0] result_o`
- `output [SOFT_THREAD*5-1:0] fflags_o`
- `output [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] ctrl_regindex_o`
- `output [`DEPTH_WARP-1:0] ctrl_warpid_o`
- `output [SOFT_THREAD-1:0] ctrl_vecmask_o`
- `output [1] ctrl_wvd_o`
- `output [1] ctrl_wxd_o`

## Submodule Instances
- `U_scalar_fpu_with_ctrl`
- `U_scalar_fpu_without_ctrl`
