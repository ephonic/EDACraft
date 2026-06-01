# warp_scheduler

## Ports (36)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] warpReq_valid_i`
- `input [`TAG_WIDTH-1:0] warpReq_dispatch2cu_wf_tag_dispatch_i`
- `input [`DEPTH_WARP-1:0] warpReq_wid_i`
- `input [`MEM_ADDR_WIDTH-1:0] warpReq_dispatch2cu_start_pc_dispatch_i`
- `input [1] warpRsp_ready_i`
- `output [1] warpRsp_valid_o`
- `output [`DEPTH_WARP-1:0] warpRsp_wid_o`
- `output [`DEPTH_WARP-1:0] wg_id_lookup_o`
- `input [`TAG_WIDTH-1:0] wg_id_tag_i`
- `output [1] pc_req_valid_o`
- `output [31:0] pc_req_addr_o`
- `output [`NUM_FETCH-1:0] pc_req_mask_o`
- `output [`DEPTH_WARP-1:0] pc_req_wid_o`
- `input [1] pc_rsp_valid_i`
- `input [31:0] pc_rsp_addr_i`
- `input [`NUM_FETCH-1:0] pc_rsp_mask_i`
- `input [`DEPTH_WARP-1:0] pc_rsp_wid_i`
- `input [1] pc_rsp_status_i`
- `output [1] branch_ready_o`
- `input [1] branch_valid_i`
- `input [`DEPTH_WARP-1:0] branch_wid_i`
- `input [1] branch_jump_i`
- `input [31:0] branch_new_pc_i`
- `output [1] warp_control_ready_o`
- `input [1] warp_control_valid_i`
- `input [1] warp_control_simt_stack_op_i`
- `input [`DEPTH_WARP-1:0] warp_control_wid_i`
- `input [`NUM_WARP-1:0] scoreboard_busy_i`
- `input [`NUM_WARP-1:0] ibuffer_ready_i`
- `output [`NUM_WARP-1:0] warp_ready_o`
- `output [1] flush_valid_o`
- `output [`DEPTH_WARP-1:0] flush_wid_o`
- `output [1] flushCache_valid_o`
- `output [`DEPTH_WARP-1:0] flushCache_wid_o`

## Logic Block Types
- comb
- seq_async_reset
