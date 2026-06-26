# valu_top

## Parameters
- `SOFT_THREAD = 4`
- `HARD_THREAD = 4`
- `MAX_ITER = 1`

## Ports (25)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] in_valid_i`
- `input [1] out_ready_i`
- `input [1] out2simt_ready_i`
- `input [SOFT_THREAD*`XLEN-1:0] in1_i`
- `input [SOFT_THREAD*`XLEN-1:0] in2_i`
- `input [SOFT_THREAD*`XLEN-1:0] in3_i`
- `input [SOFT_THREAD-1:0] mask_i`
- `input [5:0] ctrl_alu_fn_i`
- `input [1] ctrl_reverse_i`
- `input [1] ctrl_simt_stack_i`
- `input [`DEPTH_WARP-1:0] ctrl_wid_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] ctrl_reg_idxw_i`
- `input [1] ctrl_wvd_i`
- `output [1] in_ready_o`
- `output [1] out_valid_o`
- `output [1] out2simt_valid_o`
- `output [SOFT_THREAD*`XLEN-1:0] wb_wvd_rd_o`
- `output [SOFT_THREAD-1:0] wvd_mask_o`
- `output [1] wvd_o`
- `output [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] reg_idxw_o`
- `output [`DEPTH_WARP-1:0] warp_id_o`
- `output [SOFT_THREAD-1:0] if_mask_o`
- `output [`DEPTH_WARP-1:0] wid_o`
