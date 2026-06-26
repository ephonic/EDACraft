# sinkA

## Ports (31)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] sinkA_req_ready_i`
- `output [1] sinkA_req_valid_o`
- `output [`SET_BITS-1:0] sinkA_req_set_o`
- `output [`OP_BITS-1:0] sinkA_req_opcode_o`
- `output [`SIZE_BITS-1:0] sinkA_req_size_o`
- `output [`SOURCE_BITS-1:0] sinkA_req_source_o`
- `output [`TAG_BITS-1:0] sinkA_req_tag_o`
- `output [`OFFSET_BITS-1:0] sinkA_req_offset_o`
- `output [`PUT_BITS-1:0] sinkA_req_put_o`
- `output [`DATA_BITS-1:0] sinkA_req_data_o`
- `output [`MASK_BITS-1:0] sinkA_req_mask_o`
- `output [`PARAM_BITS-1:0] sinkA_req_param_o`
- `output [1] sinkA_a_ready_o`
- `input [1] sinkA_a_valid_i`
- `input [`OP_BITS-1:0] sinkA_a_opcode_i`
- `input [`SIZE_BITS-1:0] sinkA_a_size_i`
- `input [`SOURCE_BITS-1:0] sinkA_a_source_i`
- `input [`ADDRESS_BITS-1:0] sinkA_a_address_i`
- `input [`MASK_BITS-1:0] sinkA_a_mask_i`
- `input [`DATA_BITS-1:0] sinkA_a_data_i`
- `input [`PARAM_BITS-1:0] sinkA_a_param_i`
- `input [1] invalidate_ready_i`
- `input [1] flush_ready_i`
- `output [1] sinkA_pb_pop_ready_o`
- `input [1] sinkA_pb_pop_valid_i`
- `input [`PUT_BITS-1:0] sinkA_pb_pop_index_i`
- `output [`DATA_BITS-1:0] sinkA_pb_beat_data_o`
- `output [`MASK_BITS-1:0] sinkA_pb_beat_mask_o`
- `output [1] sinkA_empty_o`

## Logic Block Types
- seq_async_reset
