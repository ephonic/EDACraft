# dcache_control

## Ports (10)
- `input [2:0] opcode`
- `input [3:0] param`
- `output [1] is_read`
- `output [1] is_write`
- `output [1] is_lr`
- `output [1] is_sc`
- `output [1] is_amo`
- `output [1] is_flush`
- `output [1] is_invalidate`
- `output [1] is_wait_mshr`
