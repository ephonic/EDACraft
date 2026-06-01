# eth_mac_mii

## Parameters
- `TARGET = "GENERIC"`
- `CLOCK_INPUT_STYLE = "BUFIO2"`
- `ENABLE_PADDING = 1`
- `MIN_FRAME_LENGTH = 64`

## Ports (30)
- `input [1] rst`
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
- `input [1] mii_rx_clk`
- `input [3:0] mii_rxd`
- `input [1] mii_rx_dv`
- `input [1] mii_rx_er`
- `input [1] mii_tx_clk`
- `output [3:0] mii_txd`
- `output [1] mii_tx_en`
- `output [1] mii_tx_er`
- `output [1] tx_start_packet`
- `output [1] tx_error_underflow`
- `output [1] rx_start_packet`
- `output [1] rx_error_bad_frame`
- `output [1] rx_error_bad_fcs`
- `input [7:0] cfg_ifg`
- `input [1] cfg_tx_enable`
- `input [1] cfg_rx_enable`
