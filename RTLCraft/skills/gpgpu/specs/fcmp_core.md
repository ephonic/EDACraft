# fcmp_core

## Parameters
- `EXPWIDTH = 8`
- `PRECISION = 24`

## Ports (7)
- `input [EXPWIDTH+PRECISION-1:0] a_i`
- `input [EXPWIDTH+PRECISION-1:0] b_i`
- `input [1] signaling_i`
- `output [1] eq_o`
- `output [1] le_o`
- `output [1] lt_o`
- `output [4:0] fflags_o`
