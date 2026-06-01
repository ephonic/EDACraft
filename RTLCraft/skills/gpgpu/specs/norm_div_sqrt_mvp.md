# norm_div_sqrt_mvp

## Ports (20)
- `input [C_MANT_FP64+4:0] Mant_in_DI`
- `input [1] signed`
- `input [1] Sign_in_DI`
- `input [1] Div_enable_SI`
- `input [1] Sqrt_enable_SI`
- `input [1] Inf_a_SI`
- `input [1] Inf_b_SI`
- `input [1] Zero_a_SI`
- `input [1] Zero_b_SI`
- `input [1] NaN_a_SI`
- `input [1] NaN_b_SI`
- `input [1] SNaN_SI`
- `input [C_RM-1:0] RM_SI`
- `input [1] Full_precision_SI`
- `input [1] FP32_SI`
- `input [1] FP64_SI`
- `input [1] FP16_SI`
- `input [1] FP16ALT_SI`
- `output [C_EXP_FP64+C_MANT_FP64:0] Result_DO`
- `output [4:0] Fflags_SO`

## Logic Block Types
- always_comb
