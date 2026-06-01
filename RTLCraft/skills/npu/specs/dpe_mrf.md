# dpe_mrf

## Parameters
- `MODULE_ID = ""`
- `ID = 0`
- `DW = 32`
- `DEPTH = 512`
- `AW = 9`
- `EW = `EW`
- `DOTW = `DOTW`
- `NUM_DSP = DOTW/10`

## Ports (7)
- `input [1] wr_en`
- `input [AW-1:0] wr_addr`
- `input [AW-1:0] rd_addr`
- `input [DW-1:0] wr_data`
- `output [DW-1:0] rd_data`
- `input [1] clk`
- `input [1] rst`

## Logic Block Types
- seq
