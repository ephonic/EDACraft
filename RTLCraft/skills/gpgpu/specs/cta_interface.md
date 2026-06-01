# cta_interface

## Ports (26)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] host2cta_valid_i`
- `output [1] host2cta_ready_o`
- `input [`WG_ID_WIDTH-1:0] host2cta_host_wg_id_i`
- `input [`WF_COUNT_WIDTH_PER_WG-1:0] host2cta_host_num_wf_i`
- `input [`WAVE_ITEM_WIDTH-1:0] host2cta_host_wf_size_i`
- `input [`MEM_ADDR_WIDTH-1:0] host2cta_host_start_pc_i`
- `input [`WG_SIZE_X_WIDTH*3-1:0] host2cta_host_kernel_size_3d_i`
- `input [`MEM_ADDR_WIDTH-1:0] host2cta_host_pds_baseaddr_i`
- `input [`MEM_ADDR_WIDTH-1:0] host2cta_host_csr_knl_i`
- `input [`MEM_ADDR_WIDTH-1:0] host2cta_host_gds_baseaddr_i`
- `input [`VGPR_ID_WIDTH:0] host2cta_host_vgpr_size_total_i`
- `input [`SGPR_ID_WIDTH:0] host2cta_host_sgpr_size_total_i`
- `input [`LDS_ID_WIDTH:0] host2cta_host_lds_size_total_i`
- `input [`GDS_ID_WIDTH:0] host2cta_host_gds_size_total_i`
- `input [`VGPR_ID_WIDTH:0] host2cta_host_vgpr_size_per_wf_i`
- `input [`SGPR_ID_WIDTH:0] host2cta_host_sgpr_size_per_wf_i`
- `output [1] cta2host_rcvd_ack_o`
- `output [1] cta2host_valid_o`
- `input [1] cta2host_ready_i`
- `output [`WG_ID_WIDTH-1:0] cta2host_inflight_wg_buffer_host_wf_done_wg_id_o`
- `output [`NUMBER_CU-1:0] cta2warp_valid_o`
- `input [`NUMBER_CU-1:0] cta2warp_ready_i`
- `output [`NUMBER_CU*`WF_COUNT_WIDTH_PER_WG-1:0] cta2warp_dispatch2cu_wg_wf_count_o`
- `output [`NUMBER_CU*`WAVE_ITEM_WIDTH-1:0] cta2warp_dispatch2cu_wf_size_dispatch_o`
