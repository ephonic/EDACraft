# uart_rx

## Parameters
- `DATA_WIDTH = 8`

## Ports (10)
- `input [1] clk`
- `input [1] rst`
- `output [DATA_WIDTH-1:0] m_axis_tdata`
- `output [1] m_axis_tvalid`
- `input [1] m_axis_tready`
- `input [1] rxd`
- `output [1] busy`
- `output [1] overrun_error`
- `output [1] frame_error`
- `input [15:0] prescale`

## Logic Block Types
- seq
