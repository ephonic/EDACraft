# Listbuffer_no_push_opc_put_source

## Ports (12)
- `input [1] clk`
- `input [1] rst_n`
- `output [1] List_buffer_push_ready_o`
- `input [1] List_buffer_push_valid_i`
- `input [`PUT_BITS-1:0] List_buffer_push_index_i`
- `input [`DATA_BITS-1:0] List_buffer_push_data_data_i`
- `input [`MASK_BITS-1:0] List_buffer_push_data_mask_i`
- `output [`PUTLISTS-1:0] List_buffer_valid_o`
- `input [1] List_buffer_pop_valid_i`
- `input [`PUT_BITS-1:0] List_buffer_pop_data_i`
- `output [`DATA_BITS-1:0] List_buffer_data_data_o`
- `output [`MASK_BITS-1:0] List_buffer_data_mask_o`

## Logic Block Types
- seq_async_reset
