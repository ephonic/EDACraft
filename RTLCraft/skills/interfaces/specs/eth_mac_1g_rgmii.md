# eth_mac_1g_rgmii

## Parameters
- `TARGET = "GENERIC"`
- `IODDR_STYLE = "IODDR2"`
- `CLOCK_INPUT_STYLE = "BUFG"`
- `USE_CLK90 = "TRUE"`
- `ENABLE_PADDING = 1`
- `MIN_FRAME_LENGTH = 64`

## Ports (29)
- `input [1] gtx_clk`
- `input [1] gtx_clk90`
- `input [1] gtx_rst`
- `output [1] rx_clk`
- `output [1] rx_rst`
- `output [1] tx_clk`
- `output [1] tx_rst`
- `input [7:0] tx_axis_tdata`
- `input [1] tx_axis_tvalid`
- `output [1] tx_axis_tready`
- `input [1] tx_axis_tlast`
- `input [1] tx_axis_tuser`
- `output [7:0] rx_axis_tdata`
- `output [1] rx_axis_tvalid`
- `output [1] rx_axis_tlast`
- `output [1] rx_axis_tuser`
- `input [1] rgmii_rx_clk`
- `input [3:0] rgmii_rxd`
- `input [1] rgmii_rx_ctl`
- `output [1] rgmii_tx_clk`
- `output [3:0] rgmii_txd`
- `output [1] rgmii_tx_ctl`
- `output [1] tx_error_underflow`
- `output [1] rx_error_bad_frame`
- `output [1] rx_error_bad_fcs`
- `output [1:0] speed`
- `input [7:0] cfg_ifg`
- `input [1] cfg_tx_enable`
- `input [1] cfg_rx_enable`

## Logic Block Types
- seq
