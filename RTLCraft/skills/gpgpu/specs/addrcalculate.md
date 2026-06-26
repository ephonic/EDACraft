# addrcalculate

## Parameters
- `SHARED_ADDR_MAX = 32'd4096)(`
- `DCACHE_TAGBITS = `DCACHE_TAGBITS`

## Ports (28)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] from_fifo_valid_i`
- `output [1] from_fifo_ready_o`
- `input [`XLEN*`NUM_THREAD-1:0] from_fifo_in1_i`
- `input [`XLEN*`NUM_THREAD-1:0] from_fifo_in2_i`
- `input [`XLEN*`NUM_THREAD-1:0] from_fifo_in3_i`
- `input [`NUM_THREAD-1:0] from_fifo_mask_i`
- `input [`DEPTH_WARP-1:0] from_fifo_wid_i`
- `input [1] from_fifo_isvec_i`
- `input [1:0] from_fifo_mem_whb_i`
- `input [1] from_fifo_mem_unsigned_i`
- `input [5:0] from_fifo_alu_fn_i`
- `input [1] from_fifo_is_vls12_i`
- `input [1] from_fifo_disable_mask_i`
- `input [1:0] from_fifo_mem_cmd_i`
- `input [1:0] from_fifo_mop_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] from_fifo_reg_idxw_i`
- `input [1] from_fifo_wvd_i`
- `input [1] from_fifo_fence_i`
- `input [1] from_fifo_wxd_i`
- `input [1] from_fifo_atomic_i`
- `input [1] from_fifo_aq_i`
- `input [1] from_fifo_rl_i`
- `input [`XLEN-1:0] csr_pds_i`
- `input [`XLEN-1:0] csr_numw_i`
- `input [`XLEN-1:0] csr_tid_i`
- `output [`DEPTH_WARP-1:0] csr_wid_o`

## FSM States
- `S_IDLE` = 0

## Logic Block Types
- comb
- seq_async_reset
