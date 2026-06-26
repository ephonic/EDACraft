# ram

## Parameters
- `WORD_SIZE = 32`
- `ADDR_SIZE = 3`
- `NUM_WORDS = 8`

## Ports (8)
- `input [1] clk`
- `input [1] rst_n`
- `input [ADDR_SIZE-1:0] rd_addr_i`
- `input [ADDR_SIZE-1:0] wr_addr_i`
- `input [WORD_SIZE-1:0] wr_word_i`
- `input [1] wr_en_i`
- `input [1] rd_en_i`
- `output [WORD_SIZE-1:0] rd_word_o`

## Submodule Instances
- `SRAM`
- `U_dualportSRAM`
