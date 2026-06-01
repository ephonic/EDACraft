# axis_frame_join

## Parameters
- `S_COUNT = 4`
- `DATA_WIDTH = 8`
- `TAG_ENABLE = 1`
- `TAG_WIDTH = 16`
- `CL_S_COUNT = $clog2(S_COUNT)`
- `TAG_WORD_WIDTH = (TAG_WIDTH + DATA_WIDTH - 1) / DATA_WIDTH`
- `CL_TAG_WORD_WIDTH = $clog2(TAG_WORD_WIDTH)`

## Ports (14)
- `input [1] clk`
- `input [1] rst`
- `input [S_COUNT*DATA_WIDTH-1:0] s_axis_tdata`
- `input [S_COUNT-1:0] s_axis_tvalid`
- `output [S_COUNT-1:0] s_axis_tready`
- `input [S_COUNT-1:0] s_axis_tlast`
- `input [S_COUNT-1:0] s_axis_tuser`
- `output [DATA_WIDTH-1:0] m_axis_tdata`
- `output [1] m_axis_tvalid`
- `input [1] m_axis_tready`
- `output [1] m_axis_tlast`
- `output [1] m_axis_tuser`
- `input [TAG_WIDTH-1:0] tag`
- `output [1] busy`

## Logic Block Types
- seq
