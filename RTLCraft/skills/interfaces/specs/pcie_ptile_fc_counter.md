# pcie_ptile_fc_counter

## Parameters
- `WIDTH = 16`
- `INDEX = 0`

## Ports (6)
- `input [1] clk`
- `input [1] rst`
- `input [WIDTH-1:0] tx_cdts_limit`
- `input [2:0] tx_cdts_limit_tdm_idx`
- `input [WIDTH-1:0] fc_dec`
- `output [WIDTH-1:0] fc_av`

## Logic Block Types
- seq
