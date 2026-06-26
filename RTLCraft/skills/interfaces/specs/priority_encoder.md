# priority_encoder

## Parameters
- `WIDTH = 4`
- `LSB_HIGH_PRIORITY = 0`
- `LEVELS = WIDTH > 2 ? $clog2(WIDTH) : 1`
- `W = 2**LEVELS`

## Ports (3)
- `input [WIDTH-1:0] input_unencoded`
- `output [1] output_valid`
- `output [1] wire`
