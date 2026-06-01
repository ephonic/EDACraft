# prefer_select

## Parameters
- `RANGE = 2`
- `ID_WIDTH = 1`

## Ports (4)
- `input [RANGE-1:0] signal_i`
- `input [ID_WIDTH-1:0] prefer_i`
- `output [1] valid_o`
- `output [ID_WIDTH-1:0] id_o`

## Submodule Instances
- `U_fixed_pri_arb`
- `U_one2bin`
