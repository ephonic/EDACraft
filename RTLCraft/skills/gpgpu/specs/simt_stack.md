# simt_stack

## Ports (24)
- `input [1] clk`
- `input [1] rst_n`
- `output [1] branch_ctl_ready_o`
- `input [1] branch_ctl_valid_i`
- `input [1] branch_ctl_opcode_i`
- `input [`DEPTH_WARP-1:0] branch_ctl_wid_i`
- `input [31:0] branch_ctl_pc_branch_i`
- `input [31:0] branch_ctl_pc_execute_i`
- `input [`NUM_THREAD-1:0] branch_ctl_mask_init_i`
- `output [1] if_mask_ready_o`
- `input [1] if_mask_valid_i`
- `input [`NUM_THREAD-1:0] if_mask_mask_i`
- `input [`DEPTH_WARP-1:0] if_mask_wid_i`
- `input [1] pc_reconv_valid_i`
- `input [`XLEN-1:0] pc_reconv_i`
- `input [`DEPTH_WARP-1:0] input_wid_i`
- `output [`NUM_THREAD-1:0] out_mask_o`
- `output [1] complete_valid_o`
- `output [`DEPTH_WARP-1:0] complete_wid_o`
- `input [1] fetch_ctl_ready_i`
- `output [1] fetch_ctl_valid_o`
- `output [`DEPTH_WARP-1:0] fetch_ctl_wid_o`
- `output [1] fetch_ctl_jump_o`
- `output [31:0] fetch_ctl_new_pc_o`

## Logic Block Types
- comb
- seq_async_reset
