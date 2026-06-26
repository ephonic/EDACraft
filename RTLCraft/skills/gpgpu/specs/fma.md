# fma

## Parameters
- `EXPWIDTH = 8`
- `PRECISION = 24`
- `SOFTTHREAD = 4`
- `HARDTHREAD = 4`
- `LEN = EXPWIDTH + PRECISION`

## Ports (23)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] in_valid_i`
- `output [1] in_ready_o`
- `input [2:0] in_op_i`
- `input [EXPWIDTH+PRECISION-1:0] in_a_i`
- `input [EXPWIDTH+PRECISION-1:0] in_b_i`
- `input [EXPWIDTH+PRECISION-1:0] in_c_i`
- `input [2:0] in_rm_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] in_reg_index_i`
- `input [`DEPTH_WARP-1:0] in_warp_id_i`
- `input [SOFTTHREAD-1:0] in_vec_mask_i`
- `input [1] in_wvd_i`
- `input [1] in_wxd_i`
- `output [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] out_reg_index_o`
- `output [`DEPTH_WARP-1:0] out_warp_id_o`
- `output [SOFTTHREAD-1:0] out_vec_mask_o`
- `output [1] out_wvd_o`
- `output [1] out_wxd_o`
- `output [1] out_valid_o`
- `input [1] out_ready_i`
- `output [EXPWIDTH+PRECISION-1:0] out_result_o`
- `output [4:0] out_fflags_o`
