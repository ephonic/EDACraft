# i2c_master_axil

## Parameters
- `DEFAULT_PRESCALE = 1`
- `FIXED_PRESCALE = 0`
- `CMD_FIFO = 1`
- `CMD_FIFO_DEPTH = 32`
- `WRITE_FIFO = 1`
- `WRITE_FIFO_DEPTH = 32`
- `READ_FIFO = 1`
- `READ_FIFO_DEPTH = 32`

## Ports (27)
- `input [1] clk`
- `input [1] rst`
- `input [3:0] s_axil_awaddr`
- `input [2:0] s_axil_awprot`
- `input [1] s_axil_awvalid`
- `output [1] s_axil_awready`
- `input [31:0] s_axil_wdata`
- `input [3:0] s_axil_wstrb`
- `input [1] s_axil_wvalid`
- `output [1] s_axil_wready`
- `output [1:0] s_axil_bresp`
- `output [1] s_axil_bvalid`
- `input [1] s_axil_bready`
- `input [3:0] s_axil_araddr`
- `input [2:0] s_axil_arprot`
- `input [1] s_axil_arvalid`
- `output [1] s_axil_arready`
- `output [31:0] s_axil_rdata`
- `output [1:0] s_axil_rresp`
- `output [1] s_axil_rvalid`
- `input [1] s_axil_rready`
- `input [1] i2c_scl_i`
- `output [1] i2c_scl_o`
- `output [1] i2c_scl_t`
- `input [1] i2c_sda_i`
- `output [1] i2c_sda_o`
- `output [1] i2c_sda_t`

## Logic Block Types
- seq
