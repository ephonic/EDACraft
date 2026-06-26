# preprocess_mvp

## Ports (25)
- `input [1] Clk_CI`
- `input [1] Rst_RBI`
- `input [1] Div_start_SI`
- `input [1] Sqrt_start_SI`
- `input [1] Ready_SI`
- `input [C_OP_FP64-1:0] Operand_a_DI`
- `input [C_OP_FP64-1:0] Operand_b_DI`
- `input [C_RM-1:0] RM_SI`
- `input [C_FS-1:0] Format_sel_SI`
- `output [1] Start_SO`
- `output [C_EXP_FP64:0] Exp_a_DO_norm`
- `output [C_EXP_FP64:0] Exp_b_DO_norm`
- `output [C_MANT_FP64:0] Mant_a_DO_norm`
- `output [C_MANT_FP64:0] Mant_b_DO_norm`
- `output [C_RM-1:0] RM_dly_SO`
- `output [1] Sign_z_DO`
- `output [1] Inf_a_SO`
- `output [1] Inf_b_SO`
- `output [1] Zero_a_SO`
- `output [1] Zero_b_SO`
- `output [1] NaN_a_SO`
- `output [1] NaN_b_SO`
- `output [1] SNaN_SO`
- `output [1] Special_case_SBO`
- `output [1] Special_case_dly_SBO`

## Submodule Instances
- `LOD_Ua`
- `LOD_Ub`

## Logic Block Types
- always_comb
- always_ff
