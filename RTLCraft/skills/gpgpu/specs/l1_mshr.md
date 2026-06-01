# l1_mshr

## Ports (10)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] probe_valid_i`
- `input [`BABITS-1:0] probe_blockaddr_i`
- `input [1] missreq_valid_i`
- `output [1] missreq_ready_o`
- `input [`BABITS-1:0] missreq_blockaddr_i`
- `input [`TIWIDTH-1:0] missreq_targetinfo_i`
- `input [1] missrsp_in_valid_i`
- `output [1] missrsp_in_ready_o`

## Logic Block Types
- comb
- seq_async_reset
