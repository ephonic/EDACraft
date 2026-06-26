# i2c_single_reg

## Parameters
- `FILTER_LEN = 4`
- `DEV_ADDR = 7'h70`

## Ports (11)
- `input [1] clk`
- `input [1] rst`
- `input [1] scl_i`
- `output [1] scl_o`
- `output [1] scl_t`
- `input [1] sda_i`
- `output [1] sda_o`
- `output [1] sda_t`
- `input [7:0] data_in`
- `input [1] data_latch`
- `output [7:0] data_out`

## Logic Block Types
- seq
