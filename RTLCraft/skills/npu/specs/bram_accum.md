# bram_accum

## Parameters
- `ACCW = `ACCW`
- `NDPE = `NDPE`
- `DOTW = `DOTW`
- `PRIME_DOTW = `PRIME_DOTW`
- `DOT_PER_DSP = `DOT_PER_DSP`
- `NUM_DSP = `NUM_DSP`
- `NUM_CHUNKS = NDPE/DOTW`
- `NUM_ACCUM = `NUM_ACCUM`
- `ACCIDW = `ACCIDW`

## Ports (6)
- `input [1] clk`
- `input [1] rst`
- `input [3+ACCIDW-1:0] accum_ctrl`
- `input [3*ACCW*NDPE-1:0] accum_in`
- `output [NDPE-1:0] valid_out`
- `output [3*ACCW*NDPE-1:0] accum_out`

## FSM States
- `BRAM_LATENCY` = 0

## Logic Block Types
- comb
- seq
