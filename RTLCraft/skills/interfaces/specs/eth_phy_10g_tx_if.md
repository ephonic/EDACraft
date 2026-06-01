# eth_phy_10g_tx_if

## Parameters
- `DATA_WIDTH = 64`
- `HDR_WIDTH = 2`
- `BIT_REVERSE = 0`
- `SCRAMBLER_DISABLE = 0`
- `PRBS31_ENABLE = 0`
- `SERDES_PIPELINE = 0`

## Ports (7)
- `input [1] clk`
- `input [1] rst`
- `input [DATA_WIDTH-1:0] encoded_tx_data`
- `input [HDR_WIDTH-1:0] encoded_tx_hdr`
- `output [DATA_WIDTH-1:0] serdes_tx_data`
- `output [HDR_WIDTH-1:0] serdes_tx_hdr`
- `input [1] cfg_tx_prbs31_enable`

## Logic Block Types
- seq
