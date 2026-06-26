# scalar_fpu_no_ctrl

## Parameters
- `EXPWIDTH = 8`
- `PRECISION = 24`
- `SOFT_THREAD = 4`
- `HARD_THREAD = 4`

## Ports (14)
- `input [1] clk`
- `input [1] rst_n`
- `input [5:0] op_i`
- `input [EXPWIDTH+PRECISION-1:0] a_i`
- `input [EXPWIDTH+PRECISION-1:0] b_i`
- `input [EXPWIDTH+PRECISION-1:0] c_i`
- `input [2:0] rm_i`
- `input [1] in_valid_i`
- `input [1] out_ready_i`
- `output [1] in_ready_o`
- `output [1] out_valid_o`
- `output [2:0] select_o`
- `output [63:0] result_o`
- `output [4:0] fflags_o`

## Submodule Instances
- `U_fma_no_ctrl`
- `U_fcmp_no_ctrl`
- `U_fpmv_no_ctrl`
- `U_f2i_no_ctrl`
- `U_i2f_no_ctrl`
- `U_arbiter`
- `U_one2bin`

## Logic Block Types
- comb
