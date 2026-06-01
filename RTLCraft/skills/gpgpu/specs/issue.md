# issue

## Ports (28)
- `output [1] issue_in_ready_o`
- `input [1] issue_in_valid_i`
- `input [`NUM_THREAD*`XLEN-1:0] issue_in_vExeData_in1_i`
- `input [`NUM_THREAD*`XLEN-1:0] issue_in_vExeData_in2_i`
- `input [`NUM_THREAD*`XLEN-1:0] issue_in_vExeData_in3_i`
- `input [`NUM_THREAD-1:0] issue_in_vExeData_mask_i`
- `input [`INSTLEN-1:0] issue_in_warps_control_Signals_inst_i`
- `input [`DEPTH_WARP-1:0] issue_in_warps_control_Signals_wid_i`
- `input [1] issue_in_warps_control_Signals_fp_i`
- `input [1:0] issue_in_warps_control_Signals_branch_i`
- `input [1] issue_in_warps_control_Signals_simt_stack_i`
- `input [1] issue_in_warps_control_Signals_simt_stack_op_i`
- `input [1] issue_in_warps_control_Signals_barrier_i`
- `input [1:0] issue_in_warps_control_Signals_csr_i`
- `input [1] issue_in_warps_control_Signals_reverse_i`
- `input [1] issue_in_warps_control_Signals_isvec_i`
- `input [1:0] issue_in_warps_control_Signals_mem_whb_i`
- `input [1] issue_in_warps_control_Signals_mem_unsigned_i`
- `input [5:0] issue_in_warps_control_Signals_alu_fn_i`
- `input [1] issue_in_warps_control_Signals_force_rm_rtz_i`
- `input [1] issue_in_warps_control_Signals_is_vls12_i`
- `input [1] issue_in_warps_control_Signals_mem_i`
- `input [1] issue_in_warps_control_Signals_mul_i`
- `input [1] issue_in_warps_control_Signals_tc_i`
- `input [1] issue_in_warps_control_Signals_disable_mask_i`
- `input [1] issue_in_warps_control_Signals_custom_signal_0_i`
- `input [1:0] issue_in_warps_control_Signals_mem_cmd_i`
- `input [1:0] issue_in_warps_control_Signals_mop_i`

## Logic Block Types
- comb
