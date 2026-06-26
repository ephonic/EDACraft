# branch_join_stack

## Parameters
- `ADDR_WIDTH = 2`

## Ports (13)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] push_i`
- `input [1] pop_i`
- `input [31:0] pushdata_recon_pc_i`
- `input [31:0] pushdata_jump_pc_i`
- `input [`NUM_THREAD-1:0] pushdata_new_mask_i`
- `input [`NUM_THREAD-1:0] thread_mask_i`
- `input [31:0] pc_execute_i`
- `output [1] jump_o`
- `output [31:0] new_pc_o`
- `output [`NUM_THREAD-1:0] new_mask_o`
- `output [1] stack_empty_o`

## Logic Block Types
- seq_async_reset
