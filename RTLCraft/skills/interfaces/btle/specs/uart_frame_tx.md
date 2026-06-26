# uart_frame_tx

## Parameters
- `CLK_FREQUENCE = 50_000_000`
- `BAUD_RATE = 9600`
- `PARITY = "NONE"`
- `FRAME_WD = 8`

## Ports (6)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] frame_en`
- `input [FRAME_WD-1:0] data_frame`
- `output [1] tx_done`
- `output [1] uart_tx`

## FSM States
- `IDLE` = 0

## Logic Block Types
- comb
- seq_async_reset
