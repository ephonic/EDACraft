# eth_mac_1g_gmii

## Parameters
- `TARGET = "GENERIC"`
- `IODDR_STYLE = "IODDR2"`
- `CLOCK_INPUT_STYLE = "BUFIO2"`
- `ENABLE_PADDING = 1`
- `MIN_FRAME_LENGTH = 64`

## Ports (31)
- `input [1] gtx_clk`
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
- `input [1] gmii_rx_clk`
- `input [7:0] gmii_rxd`
- `input [1] gmii_rx_dv`
- `input [1] gmii_rx_er`
- `input [1] mii_tx_clk`
- `output [1] gmii_tx_clk`
- `output [7:0] gmii_txd`
- `output [1] gmii_tx_en`
- `output [1] gmii_tx_er`
- `output [1] tx_error_underflow`
- `output [1] rx_error_bad_frame`
- `output [1] rx_error_bad_fcs`
- `output [1:0] speed`
- `input [7:0] cfg_ifg`
- `input [1] cfg_tx_enable`
- `input [1] cfg_rx_enable`

## Logic Block Types
- seq
