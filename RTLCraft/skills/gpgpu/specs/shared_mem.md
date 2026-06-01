# shared_mem

## Ports (18)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] core_req_valid_i`
- `output [1] core_req_ready_o`
- `input [`WIDBITS-1:0] core_req_instrid_i`
- `input [1] core_req_iswrite_i`
- `input [`DCACHE_TAGBITS-1:0] core_req_tag_i`
- `input [`DCACHE_SETIDXBITS-1:0] core_req_setidx_i`
- `input [`SHAREMEM_NLANES-1:0] core_req_activemask_i`
- `input [`SHAREMEM_NLANES*`DCACHE_BLOCKOFFSETBITS-1:0] core_req_blockoffset_i`
- `input [`SHAREMEM_NLANES*`BYTESOFWORD-1:0] core_req_wordoffset1h_i`
- `input [`SHAREMEM_NLANES*`XLEN-1:0] core_req_data_i`
- `output [1] core_rsp_valid_o`
- `input [1] core_rsp_ready_i`
- `output [1] core_rsp_iswrite_o`
- `output [`WIDBITS-1:0] core_rsp_instrid_o`
- `output [`SHAREMEM_NLANES*`XLEN-1:0] core_rsp_data_o`
- `output [`SHAREMEM_NLANES-1:0] core_rsp_activemask_o`

## FSM States
- `RSP_FIFO_DEPTH` = 0
- `RSP_FIFO_CNT_DEPTH` = 1

## Logic Block Types
- comb
- seq_async_reset
