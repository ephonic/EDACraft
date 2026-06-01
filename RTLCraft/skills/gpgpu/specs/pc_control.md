# pc_control

## Ports (7)
- `input [1] clk`
- `input [1] rst_n`
- `input [31:0] new_pc_i`
- `input [1:0] pc_src_i`
- `input [`NUM_FETCH-1:0] mask_i`
- `output [31:0] pc_next_o`
- `output [`NUM_FETCH-1:0] mask_o`

## Logic Block Types
- seq_async_reset
