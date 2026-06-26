# collector_unit

## Parameters
- `S_IDLE = 2'b00`
- `S_ADD = 2'b01`
- `S_OUT = 2'b10`

## Ports (51)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] control_valid_i`
- `output [1] control_ready_o`
- `input [`DEPTH_WARP-1:0] control_wid_i`
- `input [32-1:0] control_inst_i`
- `input [6-1:0] control_imm_ext_i`
- `input [4-1:0] control_sel_imm_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] control_reg_idx1_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] control_reg_idx2_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] control_reg_idx3_i`
- `input [2-1:0] control_branch_i`
- `input [1] control_custom_signal_0_i`
- `input [1] control_isvec_i`
- `input [1] control_readmask_i`
- `input [2-1:0] control_sel_alu1_i`
- `input [2-1:0] control_sel_alu2_i`
- `input [2-1:0] control_sel_alu3_i`
- `input [32-1:0] control_pc_i`
- `input [1] control_mask_i`
- `input [1] control_fp_i`
- `input [1] control_simt_stack_i`
- `input [1] control_simt_stack_op_i`
- `input [1] control_barrier_i`
- `input [2-1:0] control_csr_i`
- `input [1] control_reverse_i`
- `input [2-1:0] control_mem_whb_i`
- `input [1] control_mem_unsigned_i`
- `input [6-1:0] control_alu_fn_i`
- `input [1] control_force_rm_rtz_i`
- `input [1] control_is_vls12_i`
- `input [1] control_mem_i`
- `input [1] control_mul_i`
- `input [1] control_tc_i`
- `input [1] control_disable_mask_i`
- `input [2-1:0] control_mem_cmd_i`
- `input [2-1:0] control_mop_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] control_reg_idxw_i`
- `input [1] control_wvd_i`
- `input [1] control_fence_i`
- `input [1] control_sfu_i`
- `input [1] control_wxd_i`
- `input [1] control_atomic_i`
- `input [1] control_aq_i`
- `input [1] control_rl_i`
- `input [2:0] control_rm_i`
- `input [1] control_rm_is_static_i`
- `input [4-1:0] bankIn_valid_i`
- `input [2*4-1:0] bankIn_regOrder_i`
- `input [`XLEN*`NUM_THREAD*4-1:0] bankIn_data_i`
- `input [`XLEN*`NUM_THREAD*4-1:0] bankIn_v0_i`

## Logic Block Types
- comb
- seq_async_reset
