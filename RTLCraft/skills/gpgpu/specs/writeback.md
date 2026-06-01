# writeback

## Parameters
- `NUM_X = 6`
- `NUM_V = 6`

## Ports (4)
- `input [NUM_X-1:0] in_x_valid_i`
- `output [NUM_X-1:0] in_x_ready_o`
- `input [`DEPTH_WARP*NUM_X-1:0] in_x_warp_id_i`
- `input [NUM_X-1:0] in_x_wxd_i`
