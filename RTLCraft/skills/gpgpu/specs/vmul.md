# vmul

## Parameters
- `SOFT_THREAD = `NUM_THREAD`
- `HARD_THREAD = `NUM_THREAD`

## Ports (27)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] in_valid_i`
- `input [1] outx_ready_i`
- `input [1] outv_ready_i`
- `input [SOFT_THREAD*`XLEN-1:0] in1_i`
- `input [SOFT_THREAD*`XLEN-1:0] in2_i`
- `input [SOFT_THREAD*`XLEN-1:0] in3_i`
- `input [SOFT_THREAD-1:0] mask_i`
- `input [5:0] ctrl_alu_fn_i`
- `input [1] ctrl_reverse_i`
- `input [`DEPTH_WARP-1:0] ctrl_wid_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] ctrl_reg_idxw_i`
- `input [1] ctrl_wvd_i`
- `input [1] ctrl_wxd_i`
- `output [1] in_ready_o`
- `output [1] outx_valid_o`
- `output [1] outv_valid_o`
- `output [`XLEN-1:0] outx_wb_wxd_rd_o`
- `output [1] outx_wxd_o`
- `output [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] outx_reg_idwx_o`
- `output [`DEPTH_WARP-1:0] outx_warp_id_o`
- `output [SOFT_THREAD*`XLEN-1:0] outv_wb_wxd_rd_o`
- `output [SOFT_THREAD-1:0] outv_wvd_mask_o`
- `output [1] outv_wvd_o`
- `output [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] outv_reg_idxw_o`
- `output [`DEPTH_WARP-1:0] outv_warp_id_o`
