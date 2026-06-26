# pipe

## Ports (40)
- `input [1] clk`
- `input [1] rst_n`
- `output [1] icache_req_valid_o`
- `output [`XLEN-1:0] icache_req_addr_o`
- `output [`NUM_FETCH-1:0] icache_req_mask_o`
- `output [`DEPTH_WARP-1:0] icache_req_wid_o`
- `input [1] icache_rsp_valid_i`
- `input [`XLEN-1:0] icache_rsp_addr_i`
- `input [`NUM_FETCH*`XLEN-1:0] icache_rsp_data_i`
- `input [`NUM_FETCH-1:0] icache_rsp_mask_i`
- `input [`DEPTH_WARP-1:0] icache_rsp_wid_i`
- `input [1] icache_rsp_status_i`
- `output [1] dcache_req_valid_o`
- `input [1] dcache_req_ready_i`
- `output [`DEPTH_WARP-1:0] dcache_req_instrid_o`
- `output [`DCACHE_SETIDXBITS-1:0] dcache_req_setidx_o`
- `output [`DCACHE_TAGBITS-1:0] dcache_req_tag_o`
- `output [`NUM_THREAD-1:0] dcache_req_activemask_o`
- `output [`NUM_THREAD*`DCACHE_BLOCKOFFSETBITS-1:0] dcache_req_blockoffset_o`
- `output [`NUM_THREAD*`BYTESOFWORD-1:0] dcache_req_wordoffset1h_o`
- `output [`NUM_THREAD*`XLEN-1:0] dcache_req_data_o`
- `output [2:0] dcache_req_opcode_o`
- `output [3:0] dcache_req_param_o`
- `input [1] dcache_rsp_valid_i`
- `output [1] dcache_rsp_ready_o`
- `input [`DEPTH_WARP-1:0] dcache_rsp_instrid_i`
- `input [`XLEN*`NUM_THREAD-1:0] dcache_rsp_data_i`
- `input [`NUM_THREAD-1:0] dcache_rsp_activemask_i`
- `output [1] shared_req_valid_o`
- `input [1] shared_req_ready_i`
- `output [`DEPTH_WARP-1:0] shared_req_instrid_o`
- `output [1] shared_req_iswrite_o`
- `output [`DCACHE_TAGBITS-1:0] shared_req_tag_o`
- `output [`DCACHE_SETIDXBITS-1:0] shared_req_setidx_o`
- `output [`NUM_THREAD-1:0] shared_req_activemask_o`
- `output [`NUM_THREAD*`DCACHE_BLOCKOFFSETBITS-1:0] shared_req_blockoffset_o`
- `output [`NUM_THREAD*`BYTESOFWORD-1:0] shared_req_wordoffset1h_o`
- `output [`NUM_THREAD*`XLEN-1:0] shared_req_data_o`
- `input [1] shared_rsp_valid_i`
- `output [1] shared_rsp_ready_o`

## FSM States
- `NUM_X` = 0

## Logic Block Types
- seq_async_reset
