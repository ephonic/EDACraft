# rgmii_phy_if

## Parameters
- `TARGET = "GENERIC"`
- `IODDR_STYLE = "IODDR2"`
- `CLOCK_INPUT_STYLE = "BUFG"`
- `USE_CLK90 = "TRUE"`

## Ports (21)
- `input [1] clk`
- `input [1] clk90`
- `input [1] rst`
- `output [1] mac_gmii_rx_clk`
- `output [1] mac_gmii_rx_rst`
- `output [7:0] mac_gmii_rxd`
- `output [1] mac_gmii_rx_dv`
- `output [1] mac_gmii_rx_er`
- `output [1] mac_gmii_tx_clk`
- `output [1] mac_gmii_tx_rst`
- `output [1] mac_gmii_tx_clk_en`
- `input [7:0] mac_gmii_txd`
- `input [1] mac_gmii_tx_en`
- `input [1] mac_gmii_tx_er`
- `input [1] phy_rgmii_rx_clk`
- `input [3:0] phy_rgmii_rxd`
- `input [1] phy_rgmii_rx_ctl`
- `output [1] phy_rgmii_tx_clk`
- `output [3:0] phy_rgmii_txd`
- `output [1] phy_rgmii_tx_ctl`
- `input [1:0] speed`

## Logic Block Types
- seq
