# host_inter

## Parameters
- `META_FNAME_SIZE = 128`
- `METADATA_SIZE = 500`
- `DATA_FNAME_SIZE = 128`
- `DATADATA_SIZE = 500`

## Ports (21)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] s_axilite_awready_o`
- `output [1] s_axilite_awvalid_i`
- `output [`AXILITE_ADDR_WIDTH-1:0] s_axilite_awaddr_i`
- `output [`AXILITE_PROT_WIDTH-1:0] s_axilite_awprot_i`
- `input [1] s_axilite_wready_o`
- `output [1] s_axilite_wvalid_i`
- `output [`AXILITE_DATA_WIDTH-1:0] s_axilite_wdata_i`
- `output [`AXILITE_STRB_WIDTH-1:0] s_axilite_wstrb_i`
- `output [1] s_axilite_bready_i`
- `input [1] s_axilite_bvalid_o`
- `input [`AXILITE_RESP_WIDTH-1:0] s_axilite_bresp_o`
- `input [1] s_axilite_arready_o`
- `output [1] s_axilite_arvalid_i`
- `output [`AXILITE_ADDR_WIDTH-1:0] s_axilite_araddr_i`
- `output [`AXILITE_PROT_WIDTH-1:0] s_axilite_arprot_i`
- `output [1] s_axilite_rready_i`
- `input [`AXILITE_DATA_WIDTH-1:0] s_axilite_rdata_o`
- `input [`AXILITE_RESP_WIDTH-1:0] s_axilite_rresp_o`
- `input [1] s_axilite_rvalid_o`
