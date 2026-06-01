# mshr_backup

## Ports (12)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] from_addr_valid_i`
- `output [1] from_addr_ready_o`
- `input [`DEPTH_WARP-1:0] from_addr_warp_id_i`
- `input [1] from_addr_wfd_i`
- `input [1] from_addr_wxd_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] from_addr_reg_idxw_i`
- `input [`NUM_THREAD-1:0] from_addr_mask_i`
- `input [1] from_addr_unsigned_i`
- `input [`BYTESOFWORD*`NUM_THREAD-1:0] from_addr_wordoffset1h_i`
- `input [1] from_addr_iswrite_i`

## FSM States
- `S_IDLE` = 0

## Logic Block Types
- comb
- seq_async_reset
