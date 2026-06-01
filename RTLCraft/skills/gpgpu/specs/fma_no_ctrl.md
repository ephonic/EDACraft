# fma_no_ctrl

## Parameters
- `EXPWIDTH = 8`
- `PRECISION = 24`
- `SOFTTHREAD = 4`
- `HARDTHREAD = 4`
- `LEN = EXPWIDTH + PRECISION`

## Ports (13)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] in_valid_i`
- `output [1] in_ready_o`
- `input [2:0] in_op_i`
- `input [EXPWIDTH+PRECISION-1:0] in_a_i`
- `input [EXPWIDTH+PRECISION-1:0] in_b_i`
- `input [EXPWIDTH+PRECISION-1:0] in_c_i`
- `input [2:0] in_rm_i`
- `output [1] out_valid_o`
- `input [1] out_ready_i`
- `output [EXPWIDTH+PRECISION-1:0] out_result_o`
- `output [4:0] out_fflags_o`
