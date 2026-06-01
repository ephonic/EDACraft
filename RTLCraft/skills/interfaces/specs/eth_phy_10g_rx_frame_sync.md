# eth_phy_10g_rx_frame_sync

## Parameters
- `HDR_WIDTH = 2`
- `BITSLIP_HIGH_CYCLES = 1`
- `BITSLIP_LOW_CYCLES = 8`
- `BITSLIP_MAX_CYCLES = BITSLIP_HIGH_CYCLES > BITSLIP_LOW_CYCLES ? BITSLIP_HIGH_CYCLES : BITSLIP_LOW_CYCLES`
- `BITSLIP_COUNT_WIDTH = $clog2(BITSLIP_MAX_CYCLES)`

## Ports (5)
- `input [1] clk`
- `input [1] rst`
- `input [HDR_WIDTH-1:0] serdes_rx_hdr`
- `output [1] serdes_rx_bitslip`
- `output [1] rx_block_lock`

## Logic Block Types
- seq
