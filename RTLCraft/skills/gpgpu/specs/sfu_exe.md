# sfu_exe

## Parameters
- `NUM_GRP = `NUM_THREAD/`NUM_SFU`
- `EXPWIDTH = 8`
- `PRECISION = 24`
- `S_IDLE = 2'b00`

## Ports (30)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] in_valid_i`
- `output [1] in_ready_o`
- `input [`XLEN*`NUM_THREAD-1:0] in_in1_i`
- `input [`XLEN*`NUM_THREAD-1:0] in_in2_i`
- `input [`XLEN*`NUM_THREAD-1:0] in_in3_i`
- `input [`NUM_THREAD-1:0] in_mask_i`
- `input [`DEPTH_WARP-1:0] in_wid_i`
- `input [1] in_fp_i`
- `input [1] in_reverse_i`
- `input [1] in_isvec_i`
- `input [5:0] in_alu_fn_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] in_reg_idxw_i`
- `input [1] in_wvd_i`
- `input [1] in_wxd_i`
- `input [2:0] in_rm_i`
- `output [1] out_x_valid_o`
- `input [1] out_x_ready_i`
- `output [`DEPTH_WARP-1:0] out_x_warp_id_o`
- `output [1] out_x_wxd_o`
- `output [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] out_x_reg_idxw_o`
- `output [`XLEN-1:0] out_x_wb_wxd_rd_o`
- `output [1] out_v_valid_o`
- `input [1] out_v_ready_i`
- `output [`DEPTH_WARP-1:0] out_v_warp_id_o`
- `output [1] out_v_wvd_o`
- `output [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] out_v_reg_idxw_o`
- `output [`NUM_THREAD-1:0] out_v_wvd_mask_o`
- `output [`XLEN*`NUM_THREAD-1:0] out_v_wb_wvd_rd_o`

## Logic Block Types
- comb
- seq_async_reset
