# axi4lite_2_cta

## Parameters
- `AXILITE_ADDR_WIDTH = 32`
- `AXILITE_DATA_WIDTH = 32`
- `AXILITE_PROT_WIDTH = 3`
- `AXILITE_RESP_WIDTH = 2`
- `AXILITE_STRB_WIDTH = 4`

## Ports (40)
- `input [1] clk`
- `input [1] rst_n`
- `output [1] host_rsp_ready_o`
- `input [1] host_rsp_valid_i`
- `input [`WG_ID_WIDTH-1:0] host_rsp_inflight_wg_buffer_host_wf_done_wg_id_i`
- `input [1] host_req_ready_i`
- `output [1] host_req_valid_o`
- `output [`WG_ID_WIDTH-1:0] host_req_wg_id_o`
- `output [`WF_COUNT_WIDTH-1:0] host_req_num_wf_o`
- `output [`WAVE_ITEM_WIDTH-1:0] host_req_wf_size_o`
- `output [`MEM_ADDR_WIDTH-1:0] host_req_start_pc_o`
- `output [`WG_SIZE_X_WIDTH*3-1:0] host_req_kernel_size_3d_o`
- `output [`MEM_ADDR_WIDTH-1:0] host_req_pds_baseaddr_o`
- `output [`MEM_ADDR_WIDTH-1:0] host_req_csr_knl_o`
- `output [`VGPR_ID_WIDTH:0] host_req_vgpr_size_total_o`
- `output [`SGPR_ID_WIDTH:0] host_req_sgpr_size_total_o`
- `output [`LDS_ID_WIDTH:0] host_req_lds_size_total_o`
- `output [`GDS_ID_WIDTH:0] host_req_gds_size_total_o`
- `output [`VGPR_ID_WIDTH:0] host_req_vgpr_size_per_wf_o`
- `output [`SGPR_ID_WIDTH:0] host_req_sgpr_size_per_wf_o`
- `output [`MEM_ADDR_WIDTH-1:0] host_req_gds_baseaddr_o`
- `output [1] s_axilite_awready_o`
- `input [1] s_axilite_awvalid_i`
- `input [AXILITE_ADDR_WIDTH-1:0] s_axilite_awaddr_i`
- `input [AXILITE_PROT_WIDTH-1:0] s_axilite_awprot_i`
- `output [1] s_axilite_wready_o`
- `input [1] s_axilite_wvalid_i`
- `input [AXILITE_DATA_WIDTH-1:0] s_axilite_wdata_i`
- `input [AXILITE_STRB_WIDTH-1:0] s_axilite_wstrb_i`
- `input [1] s_axilite_bready_i`
- `output [1] s_axilite_bvalid_o`
- `output [AXILITE_RESP_WIDTH-1:0] s_axilite_bresp_o`
- `output [1] s_axilite_arready_o`
- `input [1] s_axilite_arvalid_i`
- `input [AXILITE_ADDR_WIDTH-1:0] s_axilite_araddr_i`
- `input [AXILITE_PROT_WIDTH-1:0] s_axilite_arprot_i`
- `input [1] s_axilite_rready_i`
- `output [AXILITE_DATA_WIDTH-1:0] s_axilite_rdata_o`
- `output [AXILITE_RESP_WIDTH-1:0] s_axilite_rresp_o`
- `output [1] s_axilite_rvalid_o`

## FSM States
- `NUM_REG` = 0
- `IDLE` = 1
- `OUT_IDLE` = 2

## Logic Block Types
- seq_async_reset
