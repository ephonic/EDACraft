# ddr3_axi_retime

## Parameters
- `AXI4_RETIME_WR_REQ = 1`
- `AXI4_RETIME_WR_RESP = 1`
- `AXI4_RETIME_RD_REQ = 1`
- `AXI4_RETIME_RD_RESP = 1`
- `WIDTH = 8`
- `DEPTH = 2`
- `ADDR_W = 1`

## Ports (56)
- `input [1] clk_i`
- `input [1] rst_i`
- `input [1] inport_awvalid_i`
- `input [ 31:0] inport_awaddr_i`
- `input [  3:0] inport_awid_i`
- `input [  7:0] inport_awlen_i`
- `input [  1:0] inport_awburst_i`
- `input [1] inport_wvalid_i`
- `input [ 31:0] inport_wdata_i`
- `input [  3:0] inport_wstrb_i`
- `input [1] inport_wlast_i`
- `input [1] inport_bready_i`
- `input [1] inport_arvalid_i`
- `input [ 31:0] inport_araddr_i`
- `input [  3:0] inport_arid_i`
- `input [  7:0] inport_arlen_i`
- `input [  1:0] inport_arburst_i`
- `input [1] inport_rready_i`
- `input [1] outport_awready_i`
- `input [1] outport_wready_i`
- `input [1] outport_bvalid_i`
- `input [  1:0] outport_bresp_i`
- `input [  3:0] outport_bid_i`
- `input [1] outport_arready_i`
- `input [1] outport_rvalid_i`
- `input [ 31:0] outport_rdata_i`
- `input [  1:0] outport_rresp_i`
- `input [  3:0] outport_rid_i`
- `input [1] outport_rlast_i`
- `output [1] inport_awready_o`
- `output [1] inport_wready_o`
- `output [1] inport_bvalid_o`
- `output [  1:0] inport_bresp_o`
- `output [  3:0] inport_bid_o`
- `output [1] inport_arready_o`
- `output [1] inport_rvalid_o`
- `output [ 31:0] inport_rdata_o`
- `output [  1:0] inport_rresp_o`
- `output [  3:0] inport_rid_o`
- `output [1] inport_rlast_o`
- `output [1] outport_awvalid_o`
- `output [ 31:0] outport_awaddr_o`
- `output [  3:0] outport_awid_o`
- `output [  7:0] outport_awlen_o`
- `output [  1:0] outport_awburst_o`
- `output [1] outport_wvalid_o`
- `output [ 31:0] outport_wdata_o`
- `output [  3:0] outport_wstrb_o`
- `output [1] outport_wlast_o`
- `output [1] outport_bready_o`
- `output [1] outport_arvalid_o`
- `output [ 31:0] outport_araddr_o`
- `output [  3:0] outport_arid_o`
- `output [  7:0] outport_arlen_o`
- `output [  1:0] outport_arburst_o`
- `output [1] outport_rready_o`

## FSM States
- `WRITE_RESP_W` = 0

## Logic Block Types
- seq
