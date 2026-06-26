# uart_tx

## Parameters
- `DATA_WIDTH = 8`

## Ports (8)
- `input [1] clk`
- `input [1] rst`
- `input [DATA_WIDTH-1:0] s_axis_tdata`
- `input [1] s_axis_tvalid`
- `output [1] s_axis_tready`
- `output [1] txd`
- `output [1] busy`
- `input [15:0] prescale`

## Logic Block Types
- seq
