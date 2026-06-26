# stream_fifo_hasflush_true_no_empty_full

## Parameters
- `DATA_WIDTH = 32`
- `FIFO_DEPTH = 4`

## Ports (7)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] flush`
- `input [1] w_valid_i`
- `input [DATA_WIDTH-1:0] w_data_i`
- `input [1] r_ready_i`
- `output [DATA_WIDTH-1:0] r_data_o`
