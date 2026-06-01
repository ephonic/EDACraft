# sdpram_one_clk

## Parameters
- `DATA_WIDTH = 8`
- `ADDRESS_WIDTH = 11`

## Ports (7)
- `input [1] clk`
- `input [1] rst`
- `input [ADDRESS_WIDTH-1:0] write_address`
- `input [DATA_WIDTH-1:0] write_data`
- `input [1] write_enable`
- `input [ADDRESS_WIDTH-1:0] read_address`
- `output [DATA_WIDTH-1:0] read_data`

## Logic Block Types
- seq
