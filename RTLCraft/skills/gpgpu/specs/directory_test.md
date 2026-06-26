# directory_test

## Parameters
- `NUM_WAY = 2**`WAY_BITS`
- `NUM_SET = 2**`SET_BITS`

## Ports (41)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] dir_write_valid_i`
- `output [1] dir_write_ready_o`
- `input [`WAY_BITS-1:0] dir_write_way_i`
- `input [`TAG_BITS-1:0] dir_write_tag_i`
- `input [`SET_BITS-1:0] dir_write_set_i`
- `input [1] dir_read_valid_i`
- `output [1] dir_read_ready_o`
- `input [`SET_BITS-1:0] dir_read_set_i`
- `input [`OP_BITS-1:0] dir_read_opcode_i`
- `input [`SIZE_BITS-1:0] dir_read_size_i`
- `input [`SOURCE_BITS-1:0] dir_read_source_i`
- `input [`TAG_BITS-1:0] dir_read_tag_i`
- `input [`OFFSET_BITS-1:0] dir_read_offset_i`
- `input [`PUT_BITS-1:0] dir_read_put_i`
- `input [`DATA_BITS-1:0] dir_read_data_i`
- `input [`MASK_BITS-1:0] dir_read_mask_i`
- `input [2:0] dir_read_param_i`
- `output [1] dir_result_valid_o`
- `input [1] dir_result_ready_i`
- `output [`TAG_BITS-1:0] dir_result_victim_tag_o`
- `output [`WAY_BITS-1:0] dir_result_way_o`
- `output [1] dir_result_hit_o`
- `output [1] dir_result_dirty_o`
- `output [1] dir_result_flush_o`
- `output [1] dir_result_last_flush_o`
- `output [`SET_BITS-1:0] dir_result_set_o`
- `output [`OP_BITS-1:0] dir_result_opcode_o`
- `output [`SIZE_BITS-1:0] dir_result_size_o`
- `output [`SOURCE_BITS-1:0] dir_result_source_o`
- `output [`TAG_BITS-1:0] dir_result_tag_o`
- `output [`OFFSET_BITS-1:0] dir_result_offset_o`
- `output [`PUT_BITS-1:0] dir_result_put_o`
- `output [`DATA_BITS-1:0] dir_result_data_o`
- `output [`MASK_BITS-1:0] dir_result_mask_o`
- `output [2:0] dir_result_param_o`
- `output [1] dir_ready_o`
- `input [1] dir_flush_i`
- `input [1] dir_invalidate_i`
- `input [1] dir_tag_match_i`

## Logic Block Types
- seq_async_reset
