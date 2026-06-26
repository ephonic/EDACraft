# ptp_ts_extract

## Parameters
- `TS_WIDTH = 96`
- `TS_OFFSET = 1`
- `USER_WIDTH = TS_WIDTH+TS_OFFSET`

## Ports (7)
- `input [1] clk`
- `input [1] rst`
- `input [1] s_axis_tvalid`
- `input [1] s_axis_tlast`
- `input [USER_WIDTH-1:0] s_axis_tuser`
- `output [TS_WIDTH-1:0] m_axis_ts`
- `output [1] m_axis_ts_valid`

## Logic Block Types
- seq
