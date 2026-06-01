# int_to_fp_no_ctrl

## Parameters
- `EXPWIDTH = 8`
- `PRECISION = 24`
- `SOFT_THREAD = 4`

## Ports (11)
- `input [1] clk`
- `input [1] rst_n`
- `input [2:0] op_i`
- `input [63:0] a_i`
- `input [2:0] rm_i`
- `input [1] in_valid_i`
- `input [1] out_ready_i`
- `output [1] in_ready_o`
- `output [1] out_valid_o`
- `output [63:0] result_o`
- `output [4:0] fflags_o`

## Submodule Instances
- `U_int_to_fp_prenorm`
- `U_int_to_fp_postnorm`

## Logic Block Types
- seq_async_reset
