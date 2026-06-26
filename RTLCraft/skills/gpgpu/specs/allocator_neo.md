# allocator_neo

## Ports (31)
- `input [1] clk`
- `input [1] rst_n`
- `input [`WG_ID_WIDTH-1:0] inflight_wg_buffer_alloc_wg_id_i`
- `input [`WF_COUNT_WIDTH_PER_WG-1:0] inflight_wg_buffer_alloc_num_wf_i`
- `input [`VGPR_ID_WIDTH:0] inflight_wg_buffer_alloc_vgpr_size_i`
- `input [`SGPR_ID_WIDTH:0] inflight_wg_buffer_alloc_sgpr_size_i`
- `input [`LDS_ID_WIDTH:0] inflight_wg_buffer_alloc_lds_size_i`
- `input [`NUMBER_CU-1:0] dis_controller_cu_busy_i`
- `input [1] dis_controller_alloc_ack_i`
- `input [1] dis_controller_start_alloc_i`
- `input [1] grt_cam_up_valid_i`
- `input [`CU_ID_WIDTH-1:0] grt_cam_up_cu_id_i`
- `input [`VGPR_ID_WIDTH-1:0] grt_cam_up_vgpr_strt_i`
- `input [`VGPR_ID_WIDTH:0] grt_cam_up_vgpr_size_i`
- `input [`SGPR_ID_WIDTH-1:0] grt_cam_up_sgpr_strt_i`
- `input [`SGPR_ID_WIDTH:0] grt_cam_up_sgpr_size_i`
- `input [`LDS_ID_WIDTH-1:0] grt_cam_up_lds_strt_i`
- `input [`LDS_ID_WIDTH:0] grt_cam_up_lds_size_i`
- `input [`WF_COUNT_WIDTH-1:0] grt_cam_up_wf_count_i`
- `input [`WG_SLOT_ID_WIDTH:0] grt_cam_up_wg_count_i`
- `output [1] allocator_cu_valid_o`
- `output [1] allocator_cu_rejected_o`
- `output [`WG_ID_WIDTH-1:0] allocator_wg_id_out_o`
- `output [`CU_ID_WIDTH-1:0] allocator_cu_id_out_o`
- `output [`WF_COUNT_WIDTH_PER_WG-1:0] allocator_wf_count_o`
- `output [`VGPR_ID_WIDTH:0] allocator_vgpr_size_out_o`
- `output [`SGPR_ID_WIDTH:0] allocator_sgpr_size_out_o`
- `output [`LDS_ID_WIDTH:0] allocator_lds_size_out_o`
- `output [`VGPR_ID_WIDTH-1:0] allocator_vgpr_start_out_o`
- `output [`SGPR_ID_WIDTH-1:0] allocator_sgpr_start_out_o`
- `output [`LDS_ID_WIDTH-1:0] allocator_lds_start_out_o`

## FSM States
- `RES_SIZE_VGPR_START` = 0

## Submodule Instances
- `U_prefer_select`

## Logic Block Types
- seq_async_reset
