# eth_phy_10g_rx_ber_mon

## Parameters
- `HDR_WIDTH = 2`
- `COUNT_125US = 125000/6.4`
- `COUNT_WIDTH = $clog2($rtoi(COUNT_125US))`

## Ports (4)
- `input [1] clk`
- `input [1] rst`
- `input [HDR_WIDTH-1:0] serdes_rx_hdr`
- `output [1] rx_high_ber`

## Logic Block Types
- seq
