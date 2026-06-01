# phy_reconfig

## Ports (11)
- `output [1] reconfig_busy`
- `input [1] mgmt_clk_clk`
- `input [1] mgmt_rst_reset`
- `input [6:0] reconfig_mgmt_address`
- `input [1] reconfig_mgmt_read`
- `output [31:0] reconfig_mgmt_readdata`
- `output [1] reconfig_mgmt_waitrequest`
- `input [1] reconfig_mgmt_write`
- `input [31:0] reconfig_mgmt_writedata`
- `output [559:0] reconfig_to_xcvr`
- `input [367:0] reconfig_from_xcvr`
