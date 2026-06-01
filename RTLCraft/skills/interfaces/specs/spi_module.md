# spi_module

## Parameters
- `CPOL = 1'b0`
- `CPHA = 1'b0`
- `INVERT_DATA_ORDER = 1'b0`
- `SPI_MASTER = 1'b1`
- `SPI_WORD_LEN = 8 )`

## Ports (13)
- `input [1] master_clock`
- `output [1] SCLK_OUT`
- `input [1] SCLK_IN`
- `output [1] SS_OUT`
- `input [1] SS_IN`
- `output [1] OUTPUT_SIGNAL`
- `output [1] processing_word`
- `input [1] process_next_word`
- `input [SPI_WORD_LEN - 1:0] data_word_send`
- `input [1] INPUT_SIGNAL`
- `output [SPI_WORD_LEN - 1:0] data_word_recv`
- `input [1] do_reset`
- `output [1] is_ready`

## Logic Block Types
- seq
