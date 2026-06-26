# inflight_wg_buffer

## Ports (44)
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
- `input [1] dis_controller_wg_alloc_valid_i`
- `input [1] dis_controller_start_alloc_i`
- `input [1] dis_controller_wg_dealloc_valid_i`
- `input [1] dis_controller_wg_rejected_valid_i`
- `input [`WG_ID_WIDTH-1:0] allocator_wg_id_out_i`
- `input [`WG_ID_WIDTH-1:0] gpu_interface_dealloc_wg_id_i`
- `output [1] inflight_wg_buffer_host_rcvd_ack_o`
- `output [1] inflight_wg_buffer_host_wf_done_o`
- `output [`WG_ID_WIDTH-1:0] inflight_wg_buffer_host_wf_done_wg_id_o`
- `output [1] inflight_wg_buffer_alloc_valid_o`
- `output [1] inflight_wg_buffer_alloc_available_o`
- `output [`WG_ID_WIDTH-1:0] inflight_wg_buffer_alloc_wg_id_o`
- `output [`WF_COUNT_WIDTH_PER_WG-1:0] inflight_wg_buffer_alloc_num_wf_o`
- `output [`VGPR_ID_WIDTH:0] inflight_wg_buffer_alloc_vgpr_size_o`
- `output [`SGPR_ID_WIDTH:0] inflight_wg_buffer_alloc_sgpr_size_o`
- `output [`LDS_ID_WIDTH:0] inflight_wg_buffer_alloc_lds_size_o`
- `output [`GDS_ID_WIDTH:0] inflight_wg_buffer_alloc_gds_size_o`
- `output [1] inflight_wg_buffer_gpu_valid_o`
- `output [`VGPR_ID_WIDTH:0] inflight_wg_buffer_gpu_vgpr_size_per_wf_o`
- `output [`SGPR_ID_WIDTH:0] inflight_wg_buffer_gpu_sgpr_size_per_wf_o`
- `output [`WAVE_ITEM_WIDTH-1:0] inflight_wg_buffer_gpu_wf_size_o`
- `output [`MEM_ADDR_WIDTH-1:0] inflight_wg_buffer_start_pc_o`
- `output [`WG_SIZE_X_WIDTH*3-1:0] inflight_wg_buffer_kernel_size_3d_o`
- `output [`MEM_ADDR_WIDTH-1:0] inflight_wg_buffer_pds_baseaddr_o`
- `output [`MEM_ADDR_WIDTH-1:0] inflight_wg_buffer_csr_knl_o`
- `output [`MEM_ADDR_WIDTH-1:0] inflight_wg_buffer_gds_baseaddr_o`

## FSM States
- `SGPR_SIZE_L` = 0
- `ST_RD_HOST_IDLE` = 1
- `ST_RD_HOST_GET_FROM_HOST` = 2
- `ST_RD_HOST_ACK_TO_HOST` = 3
- `ST_RD_HOST_IDLE_BUBBLE` = 4
- `ST_ALLOC_IDLE` = 5
- `ST_ALLOC_WAIT_RESULT` = 6
- `ST_ALLOC_FIND_ACCEPTED` = 7
- `ST_ALLOC_CLEAR_ACCEPTED` = 8
- `ST_ALLOC_FIND_REJECTED` = 9
- `ST_ALLOC_CLEAR_REJECTED` = 10
- `ST_ALLOC_GET_ALLOC_WG` = 11
- `ST_ALLOC_UP_ALLOC_WG` = 12

## Submodule Instances
- `U_ram_wg_waiting_allocation`
- `U_ram_wg_ready_start`
- `U_fixed_pri_arb`
- `U_one2bin`
- `U_fixed_pri_arb_1`
- `U_one2bin_1`

## Logic Block Types
- seq_async_reset
