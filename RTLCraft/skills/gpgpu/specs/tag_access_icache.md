# tag_access_icache

## Parameters
- `TAG_WIDTH = 7`
- `NUM_SET = 32`
- `NUM_WAY = 2`
- `SET_DEPTH = 5`
- `WAY_DEPTH = 1`

## Ports (12)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] invalid_i`
- `input [1] r_req_valid_i`
- `input [SET_DEPTH-1:0] r_req_setid_i`
- `input [TAG_WIDTH-1:0] tagFromCore_st1_i`
- `input [1] w_req_valid_i`
- `input [SET_DEPTH-1:0] w_req_setid_i`
- `input [NUM_WAY*TAG_WIDTH-1:0] w_req_data_i`
- `output [NUM_SET*WAY_DEPTH-1:0] wayid_replacement_o`
- `output [WAY_DEPTH-1:0] wayid_hit_st1_o`
- `output [1] hit_st1_o`

## Logic Block Types
- seq_async_reset
