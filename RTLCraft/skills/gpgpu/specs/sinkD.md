# sinkD

## Ports (12)
- `input [1] clk`
- `input [1] rst_n`
- `input [`OP_BITS-1:0] d_opcode_i`
- `input [`SOURCE_BITS-1:0] d_source_i`
- `input [`DATA_BITS-1:0] d_data_i`
- `input [1] d_valid_i`
- `output [1] d_ready_o`
- `output [`SOURCE_BITS-1:0] source_o`
- `output [`OP_BITS-1:0] resp_opcode_o`
- `output [`SOURCE_BITS-1:0] resp_source_o`
- `output [`DATA_BITS-1:0] resp_data_o`
- `output [1] resp_valid_o`

## Logic Block Types
- seq_async_reset
