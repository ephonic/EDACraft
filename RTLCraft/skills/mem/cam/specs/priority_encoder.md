# priority_encoder

## Parameters
- `WIDTH = 4`
- `LSB_PRIORITY = "LOW"`
- `W1 = 2**$clog2(WIDTH)`
- `W2 = W1/2`

## Ports (3)
- `input [WIDTH-1:0] input_unencoded`
- `output [1] output_valid`
- `output [1] wire`
