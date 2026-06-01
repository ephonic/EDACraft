# fifo_with_count

## Parameters
- `DATA_WIDTH = 32`
- `FIFO_DEPTH = 4`
- `CNT_WIDTH = 2`

## Ports (9)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] w_en_i`
- `input [1] r_en_i`
- `input [DATA_WIDTH-1:0] w_data_i`
- `output [DATA_WIDTH-1:0] r_data_o`
- `output [1] full_o`
- `output [1] empty_o`
- `output [CNT_WIDTH-1:0] count_o`

## Logic Block Types
- seq_async_reset
