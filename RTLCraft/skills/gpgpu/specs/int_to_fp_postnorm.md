# int_to_fp_postnorm

## Parameters
- `EXPWIDTH = 8`
- `PRECISION = 24`

## Ports (7)
- `input [62:0] norm_int_i`
- `input [5:0] lzc_i`
- `input [1] is_zero_i`
- `input [1] sign_i`
- `input [2:0] rm_i`
- `output [EXPWIDTH+PRECISION-1:0] result_o`
- `output [4:0] fflags_o`

## Submodule Instances
- `U_rounding`
