# ssio_ddr_out_diff

## Parameters
- `TARGET = "GENERIC"`
- `IODDR_STYLE = "IODDR2"`
- `USE_CLK90 = "TRUE"`
- `WIDTH = 1`

## Ports (8)
- `input [1] clk`
- `input [1] clk90`
- `input [WIDTH-1:0] input_d1`
- `input [WIDTH-1:0] input_d2`
- `output [1] output_clk_p`
- `output [1] output_clk_n`
- `output [WIDTH-1:0] output_q_p`
- `output [WIDTH-1:0] output_q_n`
