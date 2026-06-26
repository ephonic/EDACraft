# fpuexe

## Parameters
- `SOFT_THREAD = `NUM_THREAD`
- `HARD_THREAD = `NUM_THREAD`

## Ports (28)
- `input [1] clk`
- `input [1] rst_n`
- `input [`NUM_THREAD*`XLEN-1:0] in1_i`
- `input [`NUM_THREAD*`XLEN-1:0] in2_i`
- `input [`NUM_THREAD*`XLEN-1:0] in3_i`
- `input [`NUM_THREAD-1:0] mask_i`
- `input [2:0] rm_i`
- `input [5:0] ctrl_alu_fn_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] ctrl_reg_idxw_i`
- `input [1] ctrl_reverse_i`
- `input [`DEPTH_WARP-1:0] ctrl_wid_i`
- `input [1] ctrl_wvd_i`
- `input [1] ctrl_wxd_i`
- `input [1] in_valid_i`
- `input [1] out_x_ready_i`
- `input [1] out_v_ready_i`
- `output [1] in_ready_o`
- `output [1] out_x_valid_o`
- `output [1] out_v_valid_o`
- `output [`XLEN-1:0] out_x_wb_wxd_rd_o`
- `output [1] out_x_wxd_o`
- `output [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] out_x_reg_idxw_o`
- `output [`DEPTH_WARP-1:0] out_x_warp_id_o`
- `output [`NUM_THREAD*`XLEN-1:0] out_v_wb_wvd_rd_o`
- `output [`NUM_THREAD-1:0] out_v_wvd_mask_o`
- `output [1] out_v_wvd_o`
- `output [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] out_v_reg_idxw_o`
- `output [`DEPTH_WARP-1:0] out_v_warp_id_o`

## Submodule Instances
- `U_vfpu`
- `U_vfpu_v2`

## Logic Block Types
- comb
