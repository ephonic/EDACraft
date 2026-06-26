# cam

## Parameters
- `DATA_WIDTH = 64`
- `ADDR_WIDTH = 5`
- `CAM_STYLE = "SRL"`
- `SLICE_WIDTH = 4`

## Ports (12)
- `input [1] clk`
- `input [1] rst`
- `input [ADDR_WIDTH-1:0] write_addr`
- `input [DATA_WIDTH-1:0] write_data`
- `input [1] write_delete`
- `input [1] write_enable`
- `output [1] write_busy`
- `input [DATA_WIDTH-1:0] compare_data`
- `output [2**ADDR_WIDTH-1:0] match_many`
- `output [2**ADDR_WIDTH-1:0] match_single`
- `output [ADDR_WIDTH-1:0] match_addr`
- `output [1] match`
