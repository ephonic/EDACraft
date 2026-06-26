# l1_dcache

## Ports (22)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] core_req_valid_i`
- `output [1] core_req_ready_o`
- `input [`WIDBITS-1:0] core_req_instrid_i`
- `input [`DCACHE_SETIDXBITS-1:0] core_req_setidx_i`
- `input [`DCACHE_TAGBITS-1:0] core_req_tag_i`
- `input [`DCACHE_NLANES-1:0] core_req_activemask_i`
- `input [`DCACHE_NLANES*`DCACHE_BLOCKOFFSETBITS-1:0] core_req_blockoffset_i`
- `input [`DCACHE_NLANES*`BYTESOFWORD-1:0] core_req_wordoffset1h_i`
- `input [`DCACHE_NLANES*`XLEN-1:0] core_req_data_i`
- `input [2:0] core_req_opcode_i`
- `input [3:0] core_req_param_i`
- `output [1] core_rsp_valid_o`
- `input [1] core_rsp_ready_i`
- `output [1] core_rsp_is_write_o`
- `output [`WIDBITS-1:0] core_rsp_instrid_o`
- `output [`DCACHE_NLANES*`XLEN-1:0] core_rsp_data_o`
- `output [`DCACHE_NLANES-1:0] core_rsp_activemask_o`
- `input [1] mem_rsp_valid_i`
- `output [1] mem_rsp_ready_o`
- `input [2:0] mem_rsp_d_opcode_i`

## Submodule Instances
- `X1060`
- `SRAM`
- `SRAM_with_count`

## Logic Block Types
- comb
- seq_async_reset
