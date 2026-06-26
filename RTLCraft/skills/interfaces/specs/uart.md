# uart

## Parameters
- `DATA_WIDTH = 8`

## Ports (15)
- `input [1] clk`
- `input [1] rst`
- `input [DATA_WIDTH-1:0] s_axis_tdata`
- `input [1] s_axis_tvalid`
- `output [1] s_axis_tready`
- `output [DATA_WIDTH-1:0] m_axis_tdata`
- `output [1] m_axis_tvalid`
- `input [1] m_axis_tready`
- `input [1] rxd`
- `output [1] txd`
- `output [1] tx_busy`
- `output [1] rx_busy`
- `output [1] rx_overrun_error`
- `output [1] rx_frame_error`
- `input [15:0] prescale`
