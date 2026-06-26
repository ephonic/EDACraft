# fmul_s1

## Parameters
- `EXPWIDTH = 8`
- `PRECISION = 24`
- `PADDINGBITS = PRECISION+2`
- `BIASINT = (1<<(EXPWIDTH-1))-1`
- `MAXNORMEXP = (1<<EXPWIDTH)-2`

## Ports (14)
- `input [EXPWIDTH+PRECISION-1:0] a_i`
- `input [EXPWIDTH+PRECISION-1:0] b_i`
- `input [2:0] rm_i`
- `output [1] out_special_case_valid_o`
- `output [1] out_special_case_nan_o`
- `output [1] out_special_case_inf_o`
- `output [1] out_special_case_inv_o`
- `output [1] out_special_case_haszero_o`
- `output [1] out_earyl_overflow_o`
- `output [1] out_prod_sign_o`
- `output [EXPWIDTH:0] out_shift_amt_o`
- `output [EXPWIDTH:0] out_exp_shifted_o`
- `output [1] out_may_be_subnormal_o`
- `output [2:0] out_rm_o`
