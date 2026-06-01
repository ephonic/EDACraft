# gpu_interface

## Ports (38)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] inflight_wg_buffer_gpu_valid_i`
- `input [`WAVE_ITEM_WIDTH-1:0] inflight_wg_buffer_gpu_wf_size_i`
- `input [`MEM_ADDR_WIDTH-1:0] inflight_wg_buffer_start_pc_i`
- `input [`WG_SIZE_X_WIDTH*3-1:0] inflight_wg_buffer_kernel_size_3d_i`
- `input [`MEM_ADDR_WIDTH-1:0] inflight_wg_buffer_pds_baseaddr_i`
- `input [`MEM_ADDR_WIDTH-1:0] inflight_wg_buffer_csr_knl_i`
- `input [`MEM_ADDR_WIDTH-1:0] inflight_wg_buffer_gds_base_dispatch_i`
- `input [`VGPR_ID_WIDTH:0] inflight_wg_buffer_gpu_vgpr_size_per_wf_i`
- `input [`SGPR_ID_WIDTH:0] inflight_wg_buffer_gpu_sgpr_size_per_wf_i`
- `input [`WG_ID_WIDTH-1:0] allocator_wg_id_out_i`
- `input [`CU_ID_WIDTH-1:0] allocator_cu_id_out_i`
- `input [`WF_COUNT_WIDTH_PER_WG-1:0] allocator_wf_count_i`
- `input [`VGPR_ID_WIDTH-1:0] allocator_vgpr_start_out_i`
- `input [`SGPR_ID_WIDTH-1:0] allocator_sgpr_start_out_i`
- `input [`LDS_ID_WIDTH-1:0] allocator_lds_start_out_i`
- `input [`NUMBER_CU-1:0] cu2dispatch_wf_done_i`
- `input [`TAG_WIDTH*`NUMBER_CU-1:0] cu2dispatch_wf_tag_done_i`
- `input [`NUMBER_CU-1:0] cu2dispatch_ready_for_dispatch_i`
- `input [1] dis_controller_wg_alloc_valid_i`
- `input [1] dis_controller_wg_dealloc_valid_i`
- `output [1] gpu_interface_alloc_available_o`
- `output [1] gpu_interface_dealloc_available_o`
- `output [`CU_ID_WIDTH-1:0] gpu_interface_cu_id_o`
- `output [`WG_ID_WIDTH-1:0] gpu_interface_dealloc_wg_id_o`
- `output [`NUMBER_CU-1:0] dispatch2cu_wf_dispatch_o`
- `output [`WF_COUNT_WIDTH_PER_WG-1:0] dispatch2cu_wg_wf_count_o`
- `output [`WAVE_ITEM_WIDTH-1:0] dispatch2cu_wf_size_dispatch_o`
- `output [`SGPR_ID_WIDTH:0] dispatch2cu_sgpr_base_dispatch_o`
- `output [`VGPR_ID_WIDTH:0] dispatch2cu_vgpr_base_dispatch_o`
- `output [`TAG_WIDTH-1:0] dispatch2cu_wf_tag_dispatch_o`
- `output [`LDS_ID_WIDTH:0] dispatch2cu_lds_base_dispatch_o`
- `output [`MEM_ADDR_WIDTH-1:0] dispatch2cu_start_pc_dispatch_o`
- `output [`WG_SIZE_X_WIDTH*3-1:0] dispatch2cu_kernel_size_3d_dispatch_o`
- `output [`MEM_ADDR_WIDTH-1:0] dispatch2cu_pds_baseaddr_dispatch_o`
- `output [`MEM_ADDR_WIDTH-1:0] dispatch2cu_csr_knl_dispatch_o`
- `output [`MEM_ADDR_WIDTH-1:0] dispatch2cu_gds_base_dispatch_o`

## FSM States
- `ST_DEALLOC_IDLE` = 0
- `ST_DEALLOC_WAIT_ACK` = 1
- `ST_ALLOC_IDLE` = 2
- `ST_ALLOC_WAIT_BUFFER` = 3
- `ST_ALLOC_WAIT_HANDLER` = 4
- `ST_ALLOC_PASS_WF` = 5

## Submodule Instances
- `U_cu_handler`
- `U_fixed_pri_arb`
- `U_one2bin`

## Logic Block Types
- seq_async_reset
