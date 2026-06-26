# SourceA

## Ports (19)
- `output [1] sourceA_req_ready_o`
- `input [1] sourceA_req_valid_i`
- `input [`SET_BITS-1:0] sourceA_req_set_i`
- `input [`OP_BITS-1:0] sourceA_req_opcode_i`
- `input [`SIZE_BITS-1:0] sourceA_req_size_i`
- `input [`SOURCE_BITS-1:0] sourceA_req_source_i`
- `input [`TAG_BITS-1:0] sourceA_req_tag_i`
- `input [`OFFSET_BITS-1:0] sourceA_req_offset_i`
- `input [`DATA_BITS-1:0] sourceA_req_data_i`
- `input [`MASK_BITS-1:0] sourceA_req_mask_i`
- `input [1] sourceA_a_ready_i`
- `output [1] sourceA_a_valid_o`
- `output [`OP_BITS-1:0] sourceA_a_opcode_o`
- `output [`SIZE_BITS-1:0] sourceA_a_size_o`
- `output [`SOURCE_BITS-1:0] sourceA_a_source_o`
- `output [`ADDRESS_BITS-1:0] sourceA_a_address_o`
- `output [`MASK_BITS-1:0] sourceA_a_mask_o`
- `output [`DATA_BITS-1:0] sourceA_a_data_o`
- `output [`PARAM_BITS-1:0] sourceA_a_param_o`
