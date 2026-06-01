# tag_checker_icache

## Parameters
- `TAG_WIDTH = 7`
- `NUM_WAY = 2`
- `WAY_DEPTH = 1`

## Ports (6)
- `input [1] r_req_valid_i`
- `input [NUM_WAY*TAG_WIDTH-1:0] tag_of_set_i`
- `input [TAG_WIDTH-1:0] tag_from_pipe_i`
- `input [NUM_WAY-1:0] way_valid_i`
- `output [WAY_DEPTH-1:0] wayid_o`
- `output [1] cache_hit_o`
