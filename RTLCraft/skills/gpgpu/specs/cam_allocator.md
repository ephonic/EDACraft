# cam_allocator

## Parameters
- `RES_ID_WIDTH = 10)`

## Ports (8)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] cam_wr_en_i`
- `input [`CU_ID_WIDTH-1:0] cam_wr_addr_i`
- `input [RES_ID_WIDTH:0] cam_wr_data_i`
- `input [1] res_search_en_i`
- `input [RES_ID_WIDTH:0] res_search_size_i`
- `output [`NUMBER_CU-1:0] res_search_out_o`

## Logic Block Types
- comb
- seq_async_reset
