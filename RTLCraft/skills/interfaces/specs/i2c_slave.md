# i2c_slave

## Parameters
- `FILTER_LEN = 4`

## Ports (24)
- `input [1] clk`
- `input [1] rst`
- `input [1] release_bus`
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
- `output [6:0] bus_address`
- `output [1] bus_addressed`
- `output [1] bus_active`
- `input [1] enable`
- `input [6:0] device_address`
- `input [6:0] device_address_mask`

## Logic Block Types
- seq
