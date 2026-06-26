# lsu2wb

## Ports (22)
- `input [1] lsu_rsp_valid_i`
- `output [1] lsu_rsp_ready_o`
- `input [`DEPTH_WARP-1:0] lsu_rsp_warp_id_i`
- `input [1] lsu_rsp_wfd_i`
- `input [1] lsu_rsp_wxd_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] lsu_rsp_reg_idxw_i`
- `input [`NUM_THREAD-1:0] lsu_rsp_mask_i`
- `input [1] lsu_rsp_iswrite_i`
- `input [`XLEN*`NUM_THREAD-1:0] lsu_rsp_data_i`
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
