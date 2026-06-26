# instruction_cache

## Ports (24)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] invalid_i`
- `input [1] core_req_valid_i`
- `input [`XLEN-1:0] core_req_addr_i`
- `input [`NUM_FETCH-1:0] core_req_mask_i`
- `input [`DEPTH_WARP-1:0] core_req_wid_i`
- `input [1] flush_pipe_valid_i`
- `input [`DEPTH_WARP-1:0] flush_pipe_wid_i`
- `output [1] core_rsp_valid_o`
- `output [`XLEN-1:0] core_rsp_addr_o`
- `output [`NUM_FETCH*`XLEN-1:0] core_rsp_data_o`
- `output [`NUM_FETCH-1:0] core_rsp_mask_o`
- `output [`DEPTH_WARP-1:0] core_rsp_wid_o`
- `output [1] core_rsp_status_o`
- `output [1] mem_rsp_ready_o`
- `input [1] mem_rsp_valid_i`
- `input [`DEPTH_WARP-1:0] mem_rsp_d_source_i`
- `input [`XLEN-1:0] mem_rsp_d_addr_i`
- `input [`DCACHE_BLOCKWORDS*`XLEN-1:0] mem_rsp_d_data_i`
- `input [1] mem_req_ready_i`
- `output [1] mem_req_valid_o`
- `output [`WIDBITS-1:0] mem_req_a_source_o`
- `output [`XLEN-1:0] mem_req_a_addr_o`

## Logic Block Types
- seq_async_reset
