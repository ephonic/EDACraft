# fadd_s2

## Parameters
- `EXPWIDTH = 8`
- `PRECISION = 24`
- `NEAR_INV = (1<<EXPWIDTH)-2`
- `INV = (1<<EXPWIDTH)-1`

## Ports (15)
- `input [2:0] in_rm_i`
- `input [1] in_far_sign_i`
- `input [EXPWIDTH-1:0] in_far_exp_i`
- `input [PRECISION+2:0] in_far_sig_i`
- `input [1] in_near_sign_i`
- `input [EXPWIDTH-1:0] in_near_exp_i`
- `input [PRECISION+2:0] in_near_sig_i`
- `input [1] in_special_case_valid_i`
- `input [1] in_special_case_iv_i`
- `input [1] in_special_case_nan_i`
- `input [1] in_far_mul_of_i`
- `input [1] in_near_sig_is_zero_i`
- `input [1] in_sel_far_path_i`
- `output [EXPWIDTH+PRECISION-1:0] out_result_o`
- `output [4:0] out_fflags_o`
