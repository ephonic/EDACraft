# aluexe

## Ports (23)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] in_valid_i`
- `input [1] out_ready_i`
- `input [1] out2br_ready_i`
- `input [`XLEN-1:0] in1_i`
- `input [`XLEN-1:0] in2_i`
- `input [`XLEN-1:0] in3_i`
- `input [`DEPTH_WARP-1:0] ctrl_wid_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] ctrl_reg_idxw_i`
- `input [1] ctrl_wxd_i`
- `input [5:0] ctrl_alu_fn_i`
- `input [1:0] ctrl_branch_i`
- `output [1] in_ready_o`
- `output [1] out_valid_o`
- `output [1] out2br_valid_o`
- `output [`XLEN-1:0] wb_wxd_rd_o`
- `output [1] wxd_o`
- `output [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] reg_idxw_o`
- `output [`DEPTH_WARP-1:0] warp_id_o`
- `output [`DEPTH_WARP-1:0] br_wid_o`
- `output [1] br_jump_o`
- `output [31:0] br_new_pc_o`

## Logic Block Types
- comb
