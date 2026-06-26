# far_path

## Parameters
- `EXPWIDTH = 8`
- `PRECISION = 48`
- `OUTPC = 24`

## Ports (10)
- `input [1] a_sign_i`
- `input [EXPWIDTH-1:0] a_exp_i`
- `input [PRECISION-1:0] a_sig_i`
- `input [PRECISION-1:0] b_sig_i`
- `input [EXPWIDTH-1:0] expdiff_i`
- `input [1] effsub_i`
- `input [1] small_add_i`
- `output [1] result_sign_o`
- `output [EXPWIDTH-1:0] result_exp_o`
- `output [OUTPC+2:0] result_sig_o`

## Logic Block Types
- comb
