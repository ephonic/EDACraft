# scoreboard

## Ports (34)
- `input [1] clk`
- `input [1] rst_n`
- `input [2-1:0] ibuffer_if_sel_alu1_i`
- `input [2-1:0] ibuffer_if_sel_alu2_i`
- `input [2-1:0] ibuffer_if_sel_alu3_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] ibuffer_if_reg_idx1_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] ibuffer_if_reg_idx2_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] ibuffer_if_reg_idx3_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] ibuffer_if_reg_idxw_i`
- `input [1] ibuffer_if_isvec_i`
- `input [1] ibuffer_if_readmask_i`
- `input [2-1:0] ibuffer_if_branch_i`
- `input [1] ibuffer_if_mask_i`
- `input [1] ibuffer_if_wxd_i`
- `input [1] ibuffer_if_wvd_i`
- `input [1] ibuffer_if_mem_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] if_reg_idxw_i`
- `input [1] if_wvd_i`
- `input [1] if_wxd_i`
- `input [2-1:0] if_branch_i`
- `input [1] if_barrier_i`
- `input [1] if_fence_i`
- `input [1] if_fire_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] wb_v_reg_idxw_i`
- `input [1] wb_v_wvd_i`
- `input [1] wb_v_fire_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] wb_x_reg_idxw_i`
- `input [1] wb_x_wxd_i`
- `input [1] wb_x_fire_i`
- `input [1] br_ctrl_i`
- `input [1] fence_end_i`
- `input [1] op_col_in_fire_i`
- `input [1] op_col_out_fire_i`
- `output [1] delay_o`

## Logic Block Types
- comb
- seq_async_reset
