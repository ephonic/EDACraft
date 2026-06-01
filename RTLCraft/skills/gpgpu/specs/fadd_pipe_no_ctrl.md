# fadd_pipe_no_ctrl

## Parameters
- `EXPWIDTH = 8`
- `PRECISION = 24`
- `SOFTTHREAD = 4`
- `HARDTHREAD = 4`
- `LEN = EXPWIDTH + PRECISION`

## Ports (20)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] in_valid_i`
- `output [1] in_ready_o`
- `input [2:0] in_op_i`
- `input [EXPWIDTH+PRECISION-1:0] in_a_i`
- `input [EXPWIDTH+PRECISION-1:0] in_b_i`
- `input [2:0] in_rm_i`
- `input [1] from_mul_fp_prod_sign_i`
- `input [EXPWIDTH-1:0] from_mul_fp_prod_exp_i`
- `input [2*PRECISION-2:0] from_mul_fp_prod_sig_i`
- `input [1] from_mul_is_nan_i`
- `input [1] from_mul_is_inf_i`
- `input [1] from_mul_is_inv_i`
- `input [1] from_mul_overflow_i`
- `input [EXPWIDTH+PRECISION-1:0] from_mul_add_another_i`
- `output [1] out_valid_o`
- `input [1] out_ready_i`
- `output [EXPWIDTH+PRECISION-1:0] out_result_o`
- `output [4:0] out_fflags_o`

## Logic Block Types
- seq_async_reset
