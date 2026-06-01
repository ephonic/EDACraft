# fp_to_int_core

## Parameters
- `EXPWIDTH = 8`
- `PRECISION = 24`

## Ports (5)
- `input [EXPWIDTH+PRECISION-1:0] a_i`
- `input [2:0] rm_i`
- `input [1:0] op_i`
- `output [63:0] result_o`
- `output [4:0] fflags_o`

## Submodule Instances
- `U_shift_right_jam`
- `U_rounding`
