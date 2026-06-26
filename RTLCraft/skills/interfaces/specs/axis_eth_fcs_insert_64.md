# axis_eth_fcs_insert_64

## Parameters
- `ENABLE_PADDING = 0`
- `MIN_FRAME_LENGTH = 64`

## Ports (15)
- `input [1] clk`
- `input [1] rst`
- `input [63:0] s_axis_tdata`
- `input [7:0] s_axis_tkeep`
- `input [1] s_axis_tvalid`
- `output [1] s_axis_tready`
- `input [1] s_axis_tlast`
- `input [1] s_axis_tuser`
- `output [63:0] m_axis_tdata`
- `output [7:0] m_axis_tkeep`
- `output [1] m_axis_tvalid`
- `input [1] m_axis_tready`
- `output [1] m_axis_tlast`
- `output [1] m_axis_tuser`
- `output [1] busy`

## Logic Block Types
- seq
