# ptp_tag_insert

## Parameters
- `DATA_WIDTH = 64`
- `KEEP_WIDTH = DATA_WIDTH/8`
- `TAG_WIDTH = 16`
- `TAG_OFFSET = 1`
- `USER_WIDTH = TAG_WIDTH+TAG_OFFSET`

## Ports (17)
- `input [1] clk`
- `input [1] rst`
- `input [DATA_WIDTH-1:0] s_axis_tdata`
- `input [KEEP_WIDTH-1:0] s_axis_tkeep`
- `input [1] s_axis_tvalid`
- `output [1] s_axis_tready`
- `input [1] s_axis_tlast`
- `input [USER_WIDTH-1:0] s_axis_tuser`
- `output [DATA_WIDTH-1:0] m_axis_tdata`
- `output [KEEP_WIDTH-1:0] m_axis_tkeep`
- `output [1] m_axis_tvalid`
- `input [1] m_axis_tready`
- `output [1] m_axis_tlast`
- `output [USER_WIDTH-1:0] m_axis_tuser`
- `input [TAG_WIDTH-1:0] s_axis_tag`
- `input [1] s_axis_tag_valid`
- `output [1] s_axis_tag_ready`

## Logic Block Types
- seq
