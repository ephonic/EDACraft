# stream_fifo_useSRAM

## Parameters
- `DATA_WIDTH = 32`
- `FIFO_DEPTH = 4`
- `ADDR_WIDTH = $clog2(FIFO_DEPTH)`

## Ports (8)
- `input [1] clk`
- `input [1] rst_n`
- `output [1] w_ready_o`
- `input [1] w_valid_i`
- `input [DATA_WIDTH-1:0] w_data_i`
- `output [1] r_valid_o`
- `input [1] r_ready_i`
- `output [DATA_WIDTH-1:0] r_data_o`

## Submodule Instances
- `SRAM`

## Logic Block Types
- seq_async_reset
