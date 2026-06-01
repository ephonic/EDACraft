# dualportSRAM

## Parameters
- `BITWIDTH = 32`
- `DEPTH = 8`

## Ports (9)
- `input [1] CLK`
- `input [1] RSTN`
- `input [BITWIDTH-1:0] D`
- `output [BITWIDTH-1:0] Q`
- `input [1] REB`
- `input [1] WEB`
- `input [BITWIDTH-1:0] BWEB`
- `input [DEPTH-1:0] AA`
- `input [DEPTH-1:0] AB`

## Logic Block Types
- seq_async_reset
