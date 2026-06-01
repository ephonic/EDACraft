# ll_axis_bridge

## Parameters
- `DATA_WIDTH = 8`

## Ports (11)
- `input [1] clk`
- `input [1] rst`
- `input [DATA_WIDTH-1:0] ll_data_in`
- `input [1] ll_sof_in_n`
- `input [1] ll_eof_in_n`
- `input [1] ll_src_rdy_in_n`
- `output [1] ll_dst_rdy_out_n`
- `output [DATA_WIDTH-1:0] m_axis_tdata`
- `output [1] m_axis_tvalid`
- `input [1] m_axis_tready`
- `output [1] m_axis_tlast`
