# uart_frame_rx

## Parameters
- `CLK_FREQUENCE = 50_000_000`
- `BAUD_RATE = 9600`
- `PARITY = "NONE"`
- `FRAME_WD = 8`

## Ports (6)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] uart_rx`
- `output [FRAME_WD-1:0] rx_frame`
- `output [1] rx_done`
- `output [1] frame_error`

## FSM States
- `IDLE` = 0

## Logic Block Types
- comb
- seq_async_reset
