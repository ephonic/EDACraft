# gmii_phy_if

## Parameters
- `TARGET = "GENERIC"`
- `IODDR_STYLE = "IODDR2"`
- `CLOCK_INPUT_STYLE = "BUFIO2"`

## Ports (22)
- `input [1] clk`
- `input [1] rst`
- `output [1] mac_gmii_rx_clk`
- `output [1] mac_gmii_rx_rst`
- `output [7:0] mac_gmii_rxd`
- `output [1] mac_gmii_rx_dv`
- `output [1] mac_gmii_rx_er`
- `output [1] mac_gmii_tx_clk`
- `output [1] mac_gmii_tx_rst`
- `input [7:0] mac_gmii_txd`
- `input [1] mac_gmii_tx_en`
- `input [1] mac_gmii_tx_er`
- `input [1] phy_gmii_rx_clk`
- `input [7:0] phy_gmii_rxd`
- `input [1] phy_gmii_rx_dv`
- `input [1] phy_gmii_rx_er`
- `input [1] phy_mii_tx_clk`
- `output [1] phy_gmii_tx_clk`
- `output [7:0] phy_gmii_txd`
- `output [1] phy_gmii_tx_en`
- `output [1] phy_gmii_tx_er`
- `input [1] mii_select`

## Logic Block Types
- seq
