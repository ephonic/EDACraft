# i2c_master

## Ports (30)
- `input [1] clk`
- `input [1] rst`
- `input [6:0] s_axis_cmd_address`
- `input [1] s_axis_cmd_start`
- `input [1] s_axis_cmd_read`
- `input [1] s_axis_cmd_write`
- `input [1] s_axis_cmd_write_multiple`
- `input [1] s_axis_cmd_stop`
- `input [1] s_axis_cmd_valid`
- `output [1] s_axis_cmd_ready`
- `input [7:0] s_axis_data_tdata`
- `input [1] s_axis_data_tvalid`
- `output [1] s_axis_data_tready`
- `input [1] s_axis_data_tlast`
- `output [7:0] m_axis_data_tdata`
- `output [1] m_axis_data_tvalid`
- `input [1] m_axis_data_tready`
- `output [1] m_axis_data_tlast`
- `input [1] scl_i`
- `output [1] scl_o`
- `output [1] scl_t`
- `input [1] sda_i`
- `output [1] sda_o`
- `output [1] sda_t`
- `output [1] busy`
- `output [1] bus_control`
- `output [1] bus_active`
- `output [1] missed_ack`
- `input [15:0] prescale`
- `input [1] stop_on_idle`

## Logic Block Types
- seq
