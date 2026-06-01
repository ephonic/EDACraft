# i2c_init

## Parameters
- `AW = $clog2(INIT_DATA_LEN)`

## Ports (16)
- `input [1] clk`
- `input [1] rst`
- `output [6:0] m_axis_cmd_address`
- `output [1] m_axis_cmd_start`
- `output [1] m_axis_cmd_read`
- `output [1] m_axis_cmd_write`
- `output [1] m_axis_cmd_write_multiple`
- `output [1] m_axis_cmd_stop`
- `output [1] m_axis_cmd_valid`
- `input [1] m_axis_cmd_ready`
- `output [7:0] m_axis_data_tdata`
- `output [1] m_axis_data_tvalid`
- `input [1] m_axis_data_tready`
- `output [1] m_axis_data_tlast`
- `output [1] busy`
- `input [1] start`

## Logic Block Types
- seq
