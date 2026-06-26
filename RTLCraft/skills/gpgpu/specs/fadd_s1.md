# fadd_s1

## Parameters
- `EXPWIDTH = 8`
- `PRECISION = 48`
- `OUTPC = 24`

## Ports (23)
- `input [EXPWIDTH+PRECISION-1:0] a_i`
- `input [EXPWIDTH+PRECISION-1:0] b_i`
- `input [2:0] rm_i`
- `input [1] b_inter_valid_i`
- `input [1] b_inter_flags_is_nan_i`
- `input [1] b_inter_flags_is_inf_i`
- `input [1] b_inter_flags_is_inv_i`
- `input [1] b_inter_flags_overflow_i`
- `output [2:0] out_rm_o`
- `output [1] out_far_sign_o`
- `output [EXPWIDTH-1:0] out_far_exp_o`
- `output [OUTPC+2:0] out_far_sig_o`
- `output [1] out_near_sign_o`
- `output [EXPWIDTH-1:0] out_near_exp_o`
- `output [OUTPC+2:0] out_near_sig_o`
- `output [1] out_special_case_valid_o`
- `output [1] out_special_case_iv_o`
- `output [1] out_special_case_nan_o`
- `output [1] out_special_case_inf_sign_o`
- `output [1] out_small_add_o`
- `output [1] out_far_mul_of_o`
- `output [1] out_near_sig_is_zero_o`
- `output [1] out_sel_far_path_o`
