# ibuffer2issue

## Ports (29)
- `input [1] clk`
- `input [1] rst_n`
- `input [`NUM_WARP*`INSTLEN-1:0] ibuffer_warps_control_Signals_inst_i`
- `input [`NUM_WARP*`DEPTH_WARP-1:0] ibuffer_warps_control_Signals_wid_i`
- `input [`NUM_WARP-1:0] ibuffer_warps_control_Signals_fp_i`
- `input [`NUM_WARP*2-1:0] ibuffer_warps_control_Signals_branch_i`
- `input [`NUM_WARP-1:0] ibuffer_warps_control_Signals_simt_stack_i`
- `input [`NUM_WARP-1:0] ibuffer_warps_control_Signals_simt_stack_op_i`
- `input [`NUM_WARP-1:0] ibuffer_warps_control_Signals_barrier_i`
- `input [`NUM_WARP*2-1:0] ibuffer_warps_control_Signals_csr_i`
- `input [`NUM_WARP-1:0] ibuffer_warps_control_Signals_reverse_i`
- `input [`NUM_WARP*2-1:0] ibuffer_warps_control_Signals_sel_alu2_i`
- `input [`NUM_WARP*2-1:0] ibuffer_warps_control_Signals_sel_alu1_i`
- `input [`NUM_WARP*2-1:0] ibuffer_warps_control_Signals_sel_alu3_i`
- `input [`NUM_WARP-1:0] ibuffer_warps_control_Signals_isvec_i`
- `input [`NUM_WARP-1:0] ibuffer_warps_control_Signals_mask_i`
- `input [`NUM_WARP*4-1:0] ibuffer_warps_control_Signals_sel_imm_i`
- `input [`NUM_WARP*2-1:0] ibuffer_warps_control_Signals_mem_whb_i`
- `input [`NUM_WARP-1:0] ibuffer_warps_control_Signals_mem_unsigned_i`
- `input [`NUM_WARP*6-1:0] ibuffer_warps_control_Signals_alu_fn_i`
- `input [`NUM_WARP-1:0] ibuffer_warps_control_Signals_force_rm_rtz_i`
- `input [`NUM_WARP-1:0] ibuffer_warps_control_Signals_is_vls12_i`
- `input [`NUM_WARP-1:0] ibuffer_warps_control_Signals_mem_i`
- `input [`NUM_WARP-1:0] ibuffer_warps_control_Signals_mul_i`
- `input [`NUM_WARP-1:0] ibuffer_warps_control_Signals_tc_i`
- `input [`NUM_WARP-1:0] ibuffer_warps_control_Signals_disable_mask_i`
- `input [`NUM_WARP-1:0] ibuffer_warps_control_Signals_custom_signal_0_i`
- `input [`NUM_WARP*2-1:0] ibuffer_warps_control_Signals_mem_cmd_i`
- `input [`NUM_WARP*2-1:0] ibuffer_warps_control_Signals_mop_i`

## Submodule Instances
- `U_round_robin_arb`
- `U_one2bin`
