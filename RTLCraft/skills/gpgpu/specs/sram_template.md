# sram_template

## Parameters
- `GEN_WIDTH = 32`
- `NUM_SET = 32`
- `NUM_WAY = 2`
- `SET_DEPTH = 5`
- `WAY_DEPTH = 1`

## Ports (9)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] r_req_valid_i`
- `input [SET_DEPTH-1:0] r_req_setid_i`
- `output [NUM_WAY*GEN_WIDTH-1:0] r_resp_data_o`
- `input [1] w_req_valid_i`
- `input [SET_DEPTH-1:0] w_req_setid_i`
- `input [NUM_WAY-1:0] w_req_waymask_i`
- `input [NUM_WAY*GEN_WIDTH-1:0] w_req_data_i`

## Submodule Instances
- `SRAM`
- `SRAM`

## Logic Block Types
- seq_async_reset
