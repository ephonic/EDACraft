# mdio_master

## Ports (17)
- `input [1] clk`
- `input [1] rst`
- `input [4:0] cmd_phy_addr`
- `input [4:0] cmd_reg_addr`
- `input [15:0] cmd_data`
- `input [1:0] cmd_opcode`
- `input [1] cmd_valid`
- `output [1] cmd_ready`
- `output [15:0] data_out`
- `output [1] data_out_valid`
- `input [1] data_out_ready`
- `output [1] mdc_o`
- `input [1] mdio_i`
- `output [1] mdio_o`
- `output [1] mdio_t`
- `output [1] busy`
- `input [7:0] prescale`

## Logic Block Types
- seq
