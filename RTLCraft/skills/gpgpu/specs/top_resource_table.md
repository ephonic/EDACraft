# top_resource_table

## Ports (31)
- `input [1] clk`
- `input [1] rst_n`
- `input [`WG_ID_WIDTH-1:0] allocator_wg_id_out_i`
- `input [`WF_COUNT_WIDTH_PER_WG-1:0] allocator_wf_count_i`
- `input [`CU_ID_WIDTH-1:0] allocator_cu_id_out_i`
- `input [`VGPR_ID_WIDTH-1:0] allocator_vgpr_start_out_i`
- `input [`VGPR_ID_WIDTH:0] allocator_vgpr_size_out_i`
- `input [`SGPR_ID_WIDTH-1:0] allocator_sgpr_start_out_i`
- `input [`SGPR_ID_WIDTH:0] allocator_sgpr_size_out_i`
- `input [`LDS_ID_WIDTH-1:0] allocator_lds_start_out_i`
- `input [`LDS_ID_WIDTH:0] allocator_lds_size_out_i`
- `input [1] dis_controller_wg_alloc_valid_i`
- `input [1] dis_controller_wg_dealloc_valid_i`
- `input [`CU_ID_WIDTH-1:0] gpu_interface_cu_id_i`
- `input [`WG_ID_WIDTH-1:0] gpu_interface_dealloc_wg_id_i`
- `output [1] grt_cam_up_valid_o`
- `output [`WF_COUNT_WIDTH-1:0] grt_cam_up_wf_count_o`
- `output [`CU_ID_WIDTH-1:0] grt_cam_up_cu_id_o`
- `output [`VGPR_ID_WIDTH-1:0] grt_cam_up_vgpr_strt_o`
- `output [`VGPR_ID_WIDTH:0] grt_cam_up_vgpr_size_o`
- `output [`SGPR_ID_WIDTH-1:0] grt_cam_up_sgpr_strt_o`
- `output [`SGPR_ID_WIDTH:0] grt_cam_up_sgpr_size_o`
- `output [`LDS_ID_WIDTH-1:0] grt_cam_up_lds_strt_o`
- `output [`LDS_ID_WIDTH:0] grt_cam_up_lds_size_o`
- `output [`WG_SLOT_ID_WIDTH:0] grt_cam_up_wg_count_o`
- `output [1] grt_wg_alloc_done_o`
- `output [`WG_ID_WIDTH-1:0] grt_wg_alloc_wg_id_o`
- `output [`CU_ID_WIDTH-1:0] grt_wg_alloc_cu_id_o`
- `output [1] grt_wg_dealloc_done_o`
- `output [`WG_ID_WIDTH-1:0] grt_wg_dealloc_wg_id_o`
- `output [`CU_ID_WIDTH-1:0] grt_wg_dealloc_cu_id_o`

## Submodule Instances
- `U_fixed_pri_arb`
- `U_one2bin`

## Logic Block Types
- seq_async_reset
