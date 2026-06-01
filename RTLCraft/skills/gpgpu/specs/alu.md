# alu

## Parameters
- `DATA_WIDTH = 32`
- `OPCODE_WIDTH = 5`

## Ports (5)
- `input [OPCODE_WIDTH-1:0] op_i`
- `input [`XLEN-1:0] in1_i`
- `input [`XLEN-1:0] in2_i`
- `output [`XLEN-1:0] out_o`
- `output [1] cmp_o`

## FSM States
- `FN_ADD` = 0
- `FN_SL` = 1
- `FN_SEQ` = 2
- `FN_SNE` = 3
- `FN_XOR` = 4
- `FN_SR` = 5
- `FN_OR` = 6
- `FN_AND` = 7
- `FN_SUB` = 8
- `FN_SRA` = 9
- `FN_SLT` = 10
- `FN_SGE` = 11
- `FN_SLTU` = 12
- `FN_SGEU` = 13
- `FN_MAX` = 14
- `FN_MIN` = 15
- `FN_MAXU` = 16
- `FN_MINU` = 17
- `FN_A1ZERO` = 18
- `FN_A2ZERO` = 19
- `FN_MUL` = 20
- `FN_MULH` = 21
- `FN_MULHU` = 22
- `FN_MULHSU` = 23
- `FN_MACC` = 24
- `FN_NMSAC` = 25
- `FN_MADD` = 26
- `FN_NMSUB` = 27
