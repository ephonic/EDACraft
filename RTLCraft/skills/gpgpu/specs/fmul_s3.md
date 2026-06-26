# fmul_s3

## Parameters
- `EXPWIDTH = 8`
- `PRECISION = 24`
- `PADDINGBITS = PRECISION+2`
- `SHIFTED = (PRECISION*3+2)+(1<<EXPWIDTH)`
- `NEAR_INV = (1<<EXPWIDTH)-2`
- `INV = (1<<EXPWIDTH)-1`

## Ports (21)
- `input [1] in_special_case_valid_i`
- `input [1] in_special_case_nan_i`
- `input [1] in_special_case_inf_i`
- `input [1] in_special_case_inv_i`
- `input [1] in_special_case_haszero_i`
- `input [1] in_earyl_overflow_i`
- `input [PRECISION*2-1:0] in_prod_i`
- `input [1] in_prod_sign_i`
- `input [EXPWIDTH:0] in_shift_amt_i`
- `input [EXPWIDTH:0] in_exp_shifted_i`
- `input [1] in_may_be_subnormal_i`
- `input [2:0] in_rm_i`
- `output [EXPWIDTH+PRECISION-1:0] result_o`
- `output [4:0] fflags_o`
- `output [1] to_fadd_fp_prod_sign_o`
- `output [EXPWIDTH-1:0] to_fadd_fp_prod_exp_o`
- `output [2*PRECISION-2:0] to_fadd_fp_prod_sig_o`
- `output [1] to_fadd_is_nan_o`
- `output [1] to_fadd_is_inf_o`
- `output [1] to_fadd_is_inv_o`
- `output [1] to_fadd_overflow_o`
