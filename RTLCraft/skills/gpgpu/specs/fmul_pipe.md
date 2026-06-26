# fmul_pipe

## Parameters
- `EXPWIDTH = 8`
- `PRECISION = 24`
- `SOFTTHREAD = 4`
- `HARDTHREAD = 4`

## Ports (32)
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
- `output [1] mul_output_fp_prod_sign_o`
- `output [EXPWIDTH-1:0] mul_output_fp_prod_exp_o`
- `output [2*PRECISION-2:0] mul_output_fp_prod_sig_o`
- `output [1] mul_output_is_nan_o`
- `output [1] mul_output_is_inf_o`
- `output [1] mul_output_is_inv_o`
- `output [1] mul_output_overflow_o`
- `output [EXPWIDTH+PRECISION-1:0] add_another_o`
- `output [2:0] op_o`

## Logic Block Types
- seq_async_reset
