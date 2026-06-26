# slowdown

## Parameters
- `NUM_FETCH = 2`
- `BUFFER_WIDTH = 155`

## Ports (11)
- `input [1] clk`
- `input [1] rst_n`
- `input [NUM_FETCH-1:0] slowdown_in_control_mask_i`
- `input [BUFFER_WIDTH*NUM_FETCH-1:0] slowdown_in_control_signals_i`
- `input [1] flush_i`
- `output [BUFFER_WIDTH-1:0] slowdown_out_control_signals_o`
- `input [1] slowdown_in_control_valid_i`
- `output [1] slowdown_in_control_ready_o`
- `output [1] slowdown_out_control_valid_o`
- `input [1] slowdown_out_control_ready_i`
- `input [1] slowdown_out_grant_i`

## Logic Block Types
- seq_async_reset
