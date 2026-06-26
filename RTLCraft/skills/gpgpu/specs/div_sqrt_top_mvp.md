# div_sqrt_top_mvp

## Ports (14)
- `input [1] Clk_CI`
- `input [1] Rst_RBI`
- `input [1] Div_start_SI`
- `input [1] Sqrt_start_SI`
- `input [C_OP_FP64-1:0] Operand_a_DI`
- `input [C_OP_FP64-1:0] Operand_b_DI`
- `input [C_RM-1:0] RM_SI`
- `input [C_PC-1:0] Precision_ctl_SI`
- `input [C_FS-1:0] Format_sel_SI`
- `input [1] Kill_SI`
- `output [C_OP_FP64-1:0] Result_DO`
- `output [4:0] Fflags_SO`
- `output [1] Ready_SO`
- `output [1] Done_SO`

## Submodule Instances
- `U0`
- `U0`
