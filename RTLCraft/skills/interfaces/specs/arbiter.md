# arbiter

## Parameters
- `PORTS = 4`
- `ARB_TYPE_ROUND_ROBIN = 0`
- `ARB_BLOCK = 0`
- `ARB_BLOCK_ACK = 1`
- `ARB_LSB_HIGH_PRIORITY = 0`

## Ports (7)
- `input [1] clk`
- `input [1] rst`
- `input [PORTS-1:0] request`
- `input [PORTS-1:0] acknowledge`
- `output [PORTS-1:0] grant`
- `output [1] grant_valid`
- `output [1] wire`

## Logic Block Types
- seq
