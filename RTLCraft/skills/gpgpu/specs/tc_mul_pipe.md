# tc_mul_pipe

## Parameters
- `EXPWIDTH = 8`
- `PRECISION = 24`
- `LATENCY = 2`

## Ports (19)
- `input [1] clk`
- `input [1] rst_n`
- `input [EXPWIDTH+PRECISION-1:0] a_i`
- `input [EXPWIDTH+PRECISION-1:0] b_i`
- `input [2:0] rm_i`
- `input [EXPWIDTH+PRECISION-1:0] ctrl_c_i`
- `input [2:0] ctrl_rm_i`
- `input [7:0] ctrl_reg_idxw_i`
- `input [`DEPTH_WARP-1:0] ctrl_warpid_i`
- `input [1] in_valid_i`
- `input [1] out_ready_i`
- `output [1] in_ready_o`
- `output [1] out_valid_o`
- `output [EXPWIDTH+PRECISION-1:0] result_o`
- `output [4:0] fflags_o`
- `output [EXPWIDTH+PRECISION-1:0] ctrl_c_o`
- `output [2:0] ctrl_rm_o`
- `output [7:0] ctrl_reg_idxw_o`
- `output [`DEPTH_WARP-1:0] ctrl_warpid_o`

## Submodule Instances
- `U_fmul_s1`
- `U_naivemultiplier`
- `U_fmul_s2`
- `U_fmul_s3`

## Logic Block Types
- seq_async_reset
