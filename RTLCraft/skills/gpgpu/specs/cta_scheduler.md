# cta_scheduler

## Ports (36)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] host_wg_valid_i`
- `output [1] host_wg_ready_o`
- `input [`WG_ID_WIDTH-1:0] host_wg_id_i`
- `input [`WF_COUNT_WIDTH_PER_WG-1:0] host_num_wf_i`
- `input [`WAVE_ITEM_WIDTH-1:0] host_wf_size_i`
- `input [`MEM_ADDR_WIDTH-1:0] host_start_pc_i`
- `input [`WG_SIZE_X_WIDTH*3-1:0] host_kernel_size_3d_i`
- `input [`MEM_ADDR_WIDTH-1:0] host_pds_baseaddr_i`
- `input [`MEM_ADDR_WIDTH-1:0] host_csr_knl_i`
- `input [`MEM_ADDR_WIDTH-1:0] host_gds_baseaddr_i`
- `input [`VGPR_ID_WIDTH:0] host_vgpr_size_total_i`
- `input [`SGPR_ID_WIDTH:0] host_sgpr_size_total_i`
- `input [`LDS_ID_WIDTH:0] host_lds_size_total_i`
- `input [`GDS_ID_WIDTH:0] host_gds_size_total_i`
- `input [`VGPR_ID_WIDTH:0] host_vgpr_size_per_wf_i`
- `input [`SGPR_ID_WIDTH:0] host_sgpr_size_per_wf_i`
- `input [`NUMBER_CU-1:0] cu2dispatch_wf_done_i`
- `input [`TAG_WIDTH*`NUMBER_CU-1:0] cu2dispatch_wf_tag_done_i`
- `input [`NUMBER_CU-1:0] cu2dispatch_ready_for_dispatch_i`
- `output [1] inflight_wg_buffer_host_rcvd_ack_o`
- `output [1] inflight_wg_buffer_host_wf_done_o`
- `output [`WG_ID_WIDTH-1:0] inflight_wg_buffer_host_wf_done_wg_id_o`
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

## Submodule Instances
- `U_allocator_neo`
- `U_top_resource_table`
- `U_inflight_wg_buffer`
- `U_gpu_interface`
- `U_dis_controller`
