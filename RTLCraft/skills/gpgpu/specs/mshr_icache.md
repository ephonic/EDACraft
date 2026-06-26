# mshr_icache

## Parameters
- `TI_WIDTH = 7`
- `BA_BITS = 7`
- `WID_BITS = 2`
- `NUM_ENTRY = 4`
- `NUM_SUB_ENTRY = 4`
- `ENTRY_DEPTH = 2`
- `SUB_ENTRY_DEPTH = 2`

## Ports (14)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] miss_req_valid_i`
- `input [BA_BITS-1:0] miss_req_block_addr_i`
- `input [TI_WIDTH-1:0] miss_req_target_info_i`
- `output [1] miss_rsp_in_ready_o`
- `input [1] miss_rsp_in_valid_i`
- `input [BA_BITS-1:0] miss_rsp_in_block_addr_i`
- `input [1] miss_rsp_out_ready_i`
- `output [BA_BITS-1:0] miss_rsp_out_block_addr_o`
- `input [1] miss2mem_ready_i`
- `output [1] miss2mem_valid_o`
- `output [BA_BITS-1:0] miss2mem_block_addr_o`
- `output [WID_BITS-1:0] miss2mem_instr_id_o`

## Logic Block Types
- seq_async_reset
