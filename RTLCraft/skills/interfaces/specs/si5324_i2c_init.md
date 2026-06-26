# si5324_i2c_init

## Parameters
- `AW = $clog2(INIT_DATA_LEN)`

## Ports (16)
- `input [1] clk`
- `input [1] rst`
- `output [6:0] cmd_address`
- `output [1] cmd_start`
- `output [1] cmd_read`
- `output [1] cmd_write`
- `output [1] cmd_write_multiple`
- `output [1] cmd_stop`
- `output [1] cmd_valid`
- `input [1] cmd_ready`
- `output [7:0] data_out`
- `output [1] data_out_valid`
- `input [1] data_out_ready`
- `output [1] data_out_last`
- `output [1] busy`
- `input [1] start`

## Logic Block Types
- seq
