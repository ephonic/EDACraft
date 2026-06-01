# axis_ll_bridge

## Parameters
- `DATA_WIDTH = 8`

## Ports (11)
- `input [1] clk`
- `input [1] rst`
- `input [DATA_WIDTH-1:0] s_axis_tdata`
- `input [1] s_axis_tvalid`
- `output [1] s_axis_tready`
- `input [1] s_axis_tlast`
- `output [DATA_WIDTH-1:0] ll_data_out`
- `output [1] ll_sof_out_n`
- `output [1] ll_eof_out_n`
- `output [1] ll_src_rdy_out_n`
- `input [1] ll_dst_rdy_in_n`

## Logic Block Types
- seq
