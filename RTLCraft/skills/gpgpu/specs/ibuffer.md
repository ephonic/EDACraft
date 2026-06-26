# ibuffer

## Parameters
- `BUFFER_WIDTH = 159`
- `SIZE_IBUFFER = 2`
- `NUM_FETCH = 2`

## Ports (32)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] ibuffer_in_valid_i`
- `output [1] ibuffer_in_ready_o`
- `input [NUM_FETCH-1:0] ibuffer_in_control_mask_i`
- `input [NUM_FETCH*`INSTLEN-1:0] ibuffer_in_control_Signals_inst_i`
- `input [NUM_FETCH*`DEPTH_WARP-1:0] ibuffer_in_control_Signals_wid_i`
- `input [NUM_FETCH-1:0] ibuffer_in_control_Signals_fp_i`
- `input [NUM_FETCH*2-1:0] ibuffer_in_control_Signals_branch_i`
- `input [NUM_FETCH-1:0] ibuffer_in_control_Signals_simt_stack_i`
- `input [NUM_FETCH-1:0] ibuffer_in_control_Signals_simt_stack_op_i`
- `input [NUM_FETCH-1:0] ibuffer_in_control_Signals_barrier_i`
- `input [NUM_FETCH*2-1:0] ibuffer_in_control_Signals_csr_i`
- `input [NUM_FETCH-1:0] ibuffer_in_control_Signals_reverse_i`
- `input [NUM_FETCH*2-1:0] ibuffer_in_control_Signals_sel_alu2_i`
- `input [NUM_FETCH*2-1:0] ibuffer_in_control_Signals_sel_alu1_i`
- `input [NUM_FETCH*2-1:0] ibuffer_in_control_Signals_sel_alu3_i`
- `input [NUM_FETCH-1:0] ibuffer_in_control_Signals_isvec_i`
- `input [NUM_FETCH-1:0] ibuffer_in_control_Signals_mask_i`
- `input [NUM_FETCH*4-1:0] ibuffer_in_control_Signals_sel_imm_i`
- `input [NUM_FETCH*2-1:0] ibuffer_in_control_Signals_mem_whb_i`
- `input [NUM_FETCH-1:0] ibuffer_in_control_Signals_mem_unsigned_i`
- `input [NUM_FETCH*6-1:0] ibuffer_in_control_Signals_alu_fn_i`
- `input [NUM_FETCH-1:0] ibuffer_in_control_Signals_force_rm_rtz_i`
- `input [NUM_FETCH-1:0] ibuffer_in_control_Signals_is_vls12_i`
- `input [NUM_FETCH-1:0] ibuffer_in_control_Signals_mem_i`
- `input [NUM_FETCH-1:0] ibuffer_in_control_Signals_mul_i`
- `input [NUM_FETCH-1:0] ibuffer_in_control_Signals_tc_i`
- `input [NUM_FETCH-1:0] ibuffer_in_control_Signals_disable_mask_i`
- `input [NUM_FETCH-1:0] ibuffer_in_control_Signals_custom_signal_0_i`
- `input [NUM_FETCH*2-1:0] ibuffer_in_control_Signals_mem_cmd_i`
- `input [NUM_FETCH*2-1:0] ibuffer_in_control_Signals_mop_i`
