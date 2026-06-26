# gpgpu_axi_top

## Ports (38)
- `input [1] clk`
- `input [1] rst_n`
- `output [1] s_axilite_awready_o`
- `input [1] s_axilite_awvalid_i`
- `input [`AXILITE_ADDR_WIDTH-1:0] s_axilite_awaddr_i`
- `input [`AXILITE_PROT_WIDTH-1:0] s_axilite_awprot_i`
- `output [1] s_axilite_wready_o`
- `input [1] s_axilite_wvalid_i`
- `input [`AXILITE_DATA_WIDTH-1:0] s_axilite_wdata_i`
- `input [`AXILITE_STRB_WIDTH-1:0] s_axilite_wstrb_i`
- `input [1] s_axilite_bready_i`
- `output [1] s_axilite_bvalid_o`
- `output [`AXILITE_RESP_WIDTH-1:0] s_axilite_bresp_o`
- `output [1] s_axilite_arready_o`
- `input [1] s_axilite_arvalid_i`
- `input [`AXILITE_ADDR_WIDTH-1:0] s_axilite_araddr_i`
- `input [`AXILITE_PROT_WIDTH-1:0] s_axilite_arprot_i`
- `input [1] s_axilite_rready_i`
- `output [`AXILITE_DATA_WIDTH-1:0] s_axilite_rdata_o`
- `output [`AXILITE_RESP_WIDTH-1:0] s_axilite_rresp_o`
- `output [1] s_axilite_rvalid_o`
- `input [1] m_axi_awready_i`
- `output [1] m_axi_awvalid_o`
- `output [`AXI_ID_WIDTH-1:0] m_axi_awid_o`
- `output [`AXI_ADDR_WIDTH-1:0] m_axi_awaddr_o`
- `output [`AXI_LEN_WIDTH-1:0] m_axi_awlen_o`
- `output [`AXI_SIZE_WIDTH-1:0] m_axi_awsize_o`
- `output [`AXI_BURST_WIDTH-1:0] m_axi_awburst_o`
- `output [1] m_axi_awlock_o`
- `output [`AXI_CACHE_WIDTH-1:0] m_axi_awcache_o`
- `output [`AXI_PROT_WIDTH-1:0] m_axi_awprot_o`
- `output [`AXI_QOS_WIDTH-1:0] m_axi_awqos_o`
- `output [`AXI_REGION_WIDTH-1:0] m_axi_awregion_o`
- `output [`AXI_ATOP_WIDTH-1:0] m_axi_awatop_o`
- `output [`AXI_USER_WIDTH-1:0] m_axi_awuser_o`
- `input [1] m_axi_wready_i`
- `output [1] m_axi_wvalid_o`
- `output [`AXI_DATA_WIDTH-1:0] m_axi_wdata_o`

## Logic Block Types
- seq_async_reset
