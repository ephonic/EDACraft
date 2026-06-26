# SdfUnit2

## Parameters
- `WIDTH = 16`
- `BF_RH = 0`

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
- `BF`
- `DelayBuffer`
- `DB`

## Logic Block Types
- seq
