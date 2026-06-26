# stream_fifo_pipe_true_has_flush

## Parameters
- `DATA_WIDTH = 32`
- `FIFO_DEPTH = 4`

## Ports (9)
- `input [1] clk`
- `input [1] rst_n`
- `output [1] w_ready_o`
- `input [1] w_valid_i`
- `input [DATA_WIDTH-1:0] w_data_i`
- `output [1] r_valid_o`
- `input [1] r_ready_i`
- `output [DATA_WIDTH-1:0] r_data_o`
- `input [1] flush`
