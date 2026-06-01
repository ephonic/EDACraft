# tag_checker

## Parameters
- `NUM_WAY = 24`
- `TAG_BITS = 2`

## Ports (5)
- `input [TAG_BITS*NUM_WAY-1:0] tag_of_set_i`
- `input [TAG_BITS-1:0] tag_from_pipe_i`
- `input [NUM_WAY-1:0] valid_of_way_i`
- `output [NUM_WAY-1:0] waymask_o`
- `output [1] cache_hit_o`
