# banked_store

## Ports (20)
- `input [1] clk`
- `input [1] rst_n`
- `input [`WAY_BITS-1:0] sinkD_adr_way_i`
- `input [`SET_BITS-1:0] sinkD_adr_set_i`
- `input [`OUTER_MASK_BITS-1:0] sinkD_adr_mask_i`
- `input [`L2CACHE_BEATBYTES*8-1:0] sinkD_dat_data_i`
- `input [1] sinkD_adr_valid_i`
- `output [1] sinkD_adr_ready_o`
- `input [`WAY_BITS-1:0] sourceD_radr_way_i`
- `input [`SET_BITS-1:0] sourceD_radr_set_i`
- `input [`INNER_MASK_BITS-1:0] sourceD_radr_mask_i`
- `output [`L2CACHE_BEATBYTES*8-1:0] sourceD_rdat_data_o`
- `input [1] sourceD_radr_valid_i`
- `output [1] sourceD_radr_ready_o`
- `input [`WAY_BITS-1:0] sourceD_wadr_way_i`
- `input [`SET_BITS-1:0] sourceD_wadr_set_i`
- `input [`INNER_MASK_BITS-1:0] sourceD_wadr_mask_i`
- `input [`L2CACHE_BEATBYTES*8-1:0] sourceD_wdat_data_i`
- `input [1] sourceD_wadr_valid_i`
- `output [1] sourceD_wadr_ready_o`

## FSM States
- `CODE_BITS` = 0
- `SINGLE_PORT` = 1

## Submodule Instances
- `U_bin2one`
- `U_cc_banks`

## Logic Block Types
- seq_async_reset
