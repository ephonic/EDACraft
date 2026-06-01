# SdfUnit

## Parameters
- `N = 64`
- `M = 64`
- `WIDTH = 16`
- `T4_EN = 0`
- `T8_EN = 1`
- `TW_FF = 1`
- `TC_FF = 1`
- `B1_RH = 0`
- `B2_RH = 1`
- `LP = 0`

## Ports (8)
- `input [1] clock`
- `input [1] reset`
- `input [1] di_en`
- `input [WIDTH-1:0] di_re`
- `input [WIDTH-1:0] di_im`
- `output [1] do_en`
- `output [WIDTH-1:0] do_re`
- `output [WIDTH-1:0] do_im`

## Submodule Instances
- `Butterfly`
- `BF1`
- `DelayBuffer`
- `DB1`
- `BF2`
- `DB2`
- `Twiddle`
- `TW`
- `TwiddleConvert4`
- `TC`
- `TwiddleConvert8`
- `Multiply`
- `MU`

## Logic Block Types
- seq
