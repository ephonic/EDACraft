# dpe

## Parameters
- `DATAW = `EW`
- `LANES = `DOTW`
- `DOTW = `PRIME_DOTW`
- `OUTW = 25`
- `REDW = `ACCW`
- `DOT_PER_DSP = `DOT_PER_DSP`
- `NUM_DSP = LANES / DOTW`
- `MULT_LATENCY = `MULT_LATENCY`
- `SIM_FLAG = 0`
- `TILE_ID = 0`
- `DPE_ID = 0`
- `DW = 32`
- `L = 3`
- `N = 2`

## Ports (11)
- `input [1] clk`
- `input [1] reset`
- `input [1] ena`
- `input [DATAW*LANES-1:0] din_a`
- `input [1] valid_a`
- `input [DATAW*DOTW-1:0] din_b`
- `input [1] _ctrl`
- `input [1] load_sel`
- `input [1] dpe_val`
- `output [DOT_PER_DSP*REDW-1:0] dout`
- `output [1] val_res`

## Logic Block Types
- seq
