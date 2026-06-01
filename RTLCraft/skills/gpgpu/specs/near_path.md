# near_path

## Parameters
- `EXPWIDTH = 8`
- `PRECISION = 48`
- `OUTPC = 24`
- `MASK_WIDTH = $clog2(PRECISION+1)`

## Ports (11)
- `input [1] a_sign_i`
- `input [EXPWIDTH-1:0] a_exp_i`
- `input [PRECISION-1:0] a_sig_i`
- `input [1] b_sign_i`
- `input [PRECISION-1:0] b_sig_i`
- `input [1] need_shift_b_i`
- `output [1] result_sign_o`
- `output [EXPWIDTH-1:0] result_exp_o`
- `output [OUTPC+2:0] result_sig_o`
- `output [1] sig_is_zero_o`
- `output [1] a_lt_b_o`
