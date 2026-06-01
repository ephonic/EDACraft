# mii_phy_if

## Parameters
- `TARGET = "GENERIC"`
- `CLOCK_INPUT_STYLE = "BUFIO2"`

## Ports (19)
- `input [1] rst`
- `output [1] mac_mii_rx_clk`
- `output [1] mac_mii_rx_rst`
- `output [3:0] mac_mii_rxd`
- `output [1] mac_mii_rx_dv`
- `output [1] mac_mii_rx_er`
- `output [1] mac_mii_tx_clk`
- `output [1] mac_mii_tx_rst`
- `input [3:0] mac_mii_txd`
- `input [1] mac_mii_tx_en`
- `input [1] mac_mii_tx_er`
- `input [1] phy_mii_rx_clk`
- `input [3:0] phy_mii_rxd`
- `input [1] phy_mii_rx_dv`
- `input [1] phy_mii_rx_er`
- `input [1] phy_mii_tx_clk`
- `output [3:0] phy_mii_txd`
- `output [1] phy_mii_tx_en`
- `output [1] phy_mii_tx_er`

## Logic Block Types
- seq
