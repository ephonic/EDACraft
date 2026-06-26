# eth_phy_10g_rx_watchdog

## Parameters
- `HDR_WIDTH = 2`
- `COUNT_125US = 125000/6.4`
- `COUNT_WIDTH = $clog2($rtoi(COUNT_125US))`

## Ports (9)
- `input [1] clk`
- `input [1] rst`
- `input [HDR_WIDTH-1:0] serdes_rx_hdr`
- `output [1] serdes_rx_reset_req`
- `input [1] rx_bad_block`
- `input [1] rx_sequence_error`
- `input [1] rx_block_lock`
- `input [1] rx_high_ber`
- `output [1] rx_status`

## Logic Block Types
- seq
