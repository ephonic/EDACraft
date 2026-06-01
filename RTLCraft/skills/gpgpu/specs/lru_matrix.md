# lru_matrix

## Parameters
- `NUM_WAY = 4`
- `WAY_DEPTH = 2`

## Ports (5)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] update_entry_i`
- `input [WAY_DEPTH-1:0] update_index_i`
- `output [WAY_DEPTH-1:0] lru_index_o`

## Submodule Instances
- `U_fixed_pri_arb`
- `U_one2bin`

## Logic Block Types
- comb
- seq_async_reset
