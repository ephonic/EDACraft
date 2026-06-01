# fmul_s2

## Parameters
- `EXPWIDTH = 8`
- `PRECISION = 24`

## Ports (24)
- `input [1] in_special_case_valid_i`
- `input [1] in_special_case_nan_i`
- `input [1] in_special_case_inf_i`
- `input [1] in_special_case_inv_i`
- `input [1] in_special_case_haszero_i`
- `input [1] in_earyl_overflow_i`
- `input [1] in_prod_sign_i`
- `input [EXPWIDTH:0] in_shift_amt_i`
- `input [EXPWIDTH:0] in_exp_shifted_i`
- `input [1] in_may_be_subnormal_i`
- `input [2:0] in_rm_i`
- `input [PRECISION*2-1:0] prod_i`
- `output [1] out_special_case_valid_o`
- `output [1] out_special_case_nan_o`
- `output [1] out_special_case_inf_o`
- `output [1] out_special_case_inv_o`
- `output [1] out_special_case_haszero_o`
- `output [1] out_earyl_overflow_o`
- `output [PRECISION*2-1:0] out_prod_o`
- `output [1] out_prod_sign_o`
- `output [EXPWIDTH:0] out_shift_amt_o`
- `output [EXPWIDTH:0] out_exp_shifted_o`
- `output [1] out_may_be_subnormal_o`
- `output [2:0] out_rm_o`
