# prime_dsp_tensor_int8

## Parameters
- `TILE_ID = 99`
- `DPE_ID = 99`
- `DSP_CASCADE = "cascade_disabled"`

## Ports (15)
- `input [1] clk`
- `input [1] clr`
- `input [1] ena`
- `input [95:0] data_in`
- `input [1] load_buf_sel`
- `input [1] load_bb_one`
- `input [1] load_bb_two`
- `input [1:0] feed_sel`
- `input [1] zero_en`
- `input [87:0] cascade_weight_in`
- `output [87:0] cascade_weight_out`
- `input [95:0] cascade_data_in`
- `output [95:0] cascade_data_out`
- `output [36:0] result_h`
- `output [37:0] result_l`

## Logic Block Types
- comb
- seq
