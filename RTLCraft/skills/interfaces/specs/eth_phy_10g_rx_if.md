# eth_phy_10g_rx_if

## Parameters
- `DATA_WIDTH = 64`
- `HDR_WIDTH = 2`
- `BIT_REVERSE = 0`
- `SCRAMBLER_DISABLE = 0`
- `PRBS31_ENABLE = 0`
- `SERDES_PIPELINE = 0`
- `BITSLIP_HIGH_CYCLES = 1`
- `BITSLIP_LOW_CYCLES = 8`
- `COUNT_125US = 125000/6.4`

## Ports (15)
- `input [1] clk`
- `input [1] rst`
- `output [DATA_WIDTH-1:0] encoded_rx_data`
- `output [HDR_WIDTH-1:0] encoded_rx_hdr`
- `input [DATA_WIDTH-1:0] serdes_rx_data`
- `input [HDR_WIDTH-1:0] serdes_rx_hdr`
- `output [1] serdes_rx_bitslip`
- `output [1] serdes_rx_reset_req`
- `input [1] rx_bad_block`
- `input [1] rx_sequence_error`
- `output [6:0] rx_error_count`
- `output [1] rx_block_lock`
- `output [1] rx_high_ber`
- `output [1] rx_status`
- `input [1] cfg_rx_prbs31_enable`

## Logic Block Types
- seq
