# nrbd_nrsc_mvp

## Ports (25)
- `input [1] Clk_CI`
- `input [1] Rst_RBI`
- `input [1] Div_start_SI`
- `input [1] Sqrt_start_SI`
- `input [1] Start_SI`
- `input [1] Kill_SI`
- `input [1] Special_case_SBI`
- `input [1] Special_case_dly_SBI`
- `input [C_PC-1:0] Precision_ctl_SI`
- `input [1:0] Format_sel_SI`
- `input [C_MANT_FP64:0] Mant_a_DI`
- `input [C_MANT_FP64:0] Mant_b_DI`
- `input [C_EXP_FP64:0] Exp_a_DI`
- `input [C_EXP_FP64:0] Exp_b_DI`
- `output [1] Div_enable_SO`
- `output [1] Sqrt_enable_SO`
- `output [1] Full_precision_SO`
- `output [1] FP32_SO`
- `output [1] FP64_SO`
- `output [1] FP16_SO`
- `output [1] FP16ALT_SO`
- `output [1] Ready_SO`
- `output [1] Done_SO`
- `output [C_MANT_FP64+4:0] Mant_z_DO`
- `output [C_EXP_FP64+1:0] Exp_z_DO`

## Submodule Instances
- `U0`
