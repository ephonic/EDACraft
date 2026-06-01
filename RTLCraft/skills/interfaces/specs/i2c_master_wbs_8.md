# i2c_master_wbs_8

## Parameters
- `DEFAULT_PRESCALE = 1`
- `FIXED_PRESCALE = 0`
- `CMD_FIFO = 1`
- `CMD_FIFO_DEPTH = 32`
- `WRITE_FIFO = 1`
- `WRITE_FIFO_DEPTH = 32`
- `READ_FIFO = 1`
- `READ_FIFO_DEPTH = 32`

## Ports (15)
- `input [1] clk`
- `input [1] rst`
- `input [2:0] wbs_adr_i`
- `input [7:0] wbs_dat_i`
- `output [7:0] wbs_dat_o`
- `input [1] wbs_we_i`
- `input [1] wbs_stb_i`
- `output [1] wbs_ack_o`
- `input [1] wbs_cyc_i`
- `input [1] i2c_scl_i`
- `output [1] i2c_scl_o`
- `output [1] i2c_scl_t`
- `input [1] i2c_sda_i`
- `output [1] i2c_sda_o`
- `output [1] i2c_sda_t`

## Logic Block Types
- seq
