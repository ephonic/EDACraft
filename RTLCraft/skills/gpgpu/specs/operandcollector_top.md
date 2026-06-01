# operandcollector_top

## Parameters
- `DEPTH_4_COLLECTORUNIT = $clog2(4*`NUM_COLLECTORUNIT)`

## Ports (60)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] in_valid_i`
- `output [1] in_ready_o`
- `input [`DEPTH_WARP-1:0] in_wid_i`
- `input [32-1:0] in_inst_i`
- `input [6-1:0] in_imm_ext_i`
- `input [4-1:0] in_sel_imm_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] in_reg_idx1_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] in_reg_idx2_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] in_reg_idx3_i`
- `input [2-1:0] in_branch_i`
- `input [1] in_custom_signal_0_i`
- `input [1] in_isvec_i`
- `input [1] in_readmask_i`
- `input [2-1:0] in_sel_alu1_i`
- `input [2-1:0] in_sel_alu2_i`
- `input [2-1:0] in_sel_alu3_i`
- `input [32-1:0] in_pc_i`
- `input [1] in_mask_i`
- `input [1] in_fp_i`
- `input [1] in_simt_stack_i`
- `input [1] in_simt_stack_op_i`
- `input [1] in_barrier_i`
- `input [2-1:0] in_csr_i`
- `input [1] in_reverse_i`
- `input [2-1:0] in_mem_whb_i`
- `input [1] in_mem_unsigned_i`
- `input [6-1:0] in_alu_fn_i`
- `input [1] in_force_rm_rtz_i`
- `input [1] in_is_vls12_i`
- `input [1] in_mem_i`
- `input [1] in_mul_i`
- `input [1] in_tc_i`
- `input [1] in_disable_mask_i`
- `input [2-1:0] in_mem_cmd_i`
- `input [2-1:0] in_mop_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] in_reg_idxw_i`
- `input [1] in_wvd_i`
- `input [1] in_fence_i`
- `input [1] in_sfu_i`
- `input [1] in_wxd_i`
- `input [1] in_atomic_i`
- `input [1] in_aq_i`
- `input [1] in_rl_i`
- `input [2:0] in_rm_i`
- `input [1] in_rm_is_static_i`
- `input [1] writeScalar_valid_i`
- `output [1] writeScalar_ready_o`
- `input [`XLEN-1:0] writeScalar_rd_i`
- `input [1] writeScalar_wxd_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] writeScalar_idxw_i`
- `input [`DEPTH_WARP-1:0] writeScalar_wid_i`
- `input [1] writeVector_valid_i`
- `output [1] writeVector_ready_o`
- `input [`XLEN*`NUM_THREAD-1:0] writeVector_rd_i`
- `input [`NUM_THREAD-1:0] writeVector_wvd_mask_i`
- `input [1] writeVector_wvd_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] writeVector_idxw_i`
- `input [`DEPTH_WARP-1:0] writeVector_wid_i`

## Submodule Instances
- `U_fixed_pri_arb`
- `U_one2bin`

## Logic Block Types
- comb
- seq_async_reset
