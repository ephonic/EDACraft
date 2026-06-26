# branch_back

## Ports (15)
- `output [1] v_ready_o`
- `input [1] v_valid_i`
- `input [`DEPTH_WARP-1:0] v_wid_i`
- `input [1] v_jump_i`
- `input [31:0] v_new_pc_i`
- `output [1] s_ready_o`
- `input [1] s_valid_i`
- `input [`DEPTH_WARP-1:0] s_wid_i`
- `input [1] s_jump_i`
- `input [31:0] s_new_pc_i`
- `input [1] out_ready_i`
- `output [1] out_valid_o`
- `output [`DEPTH_WARP-1:0] out_wid_o`
- `output [1] out_jump_o`
- `output [31:0] out_new_pc_o`

## Logic Block Types
- comb
