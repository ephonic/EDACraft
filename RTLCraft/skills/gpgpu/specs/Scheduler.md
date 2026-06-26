# Scheduler

## Parameters
- `dir_result_buffer_data_in_width = `TAG_BITS + `WAY_BITS + 4 + `SET_BITS + `L2C_BITS + `OP_BITS +`SIZE_BITS + `SOURCE_BITS + `TAG_BITS + `OFFSET_BITS + `PUT_BITS + `DATA_BITS + `MASK_BITS + `PARAM_BITS`
- `writebuffer_data_in_width = `SET_BITS + `L2C_BITS + `OP_BITS + `SIZE_BITS + `SOURCE_BITS + `TAG_BITS +  `OFFSET_BITS + `PUT_BITS + `DATA_BITS + `MASK_BITS + `PARAM_BITS`

## Ports (34)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] sche_in_a_valid_i`
- `output [1] sche_in_a_ready_o`
- `input [`OP_BITS-1:0] sche_in_a_opcode_i`
- `input [`SIZE_BITS-1:0] sche_in_a_size_i`
- `input [`SOURCE_BITS-1:0] sche_in_a_source_i`
- `input [`ADDRESS_BITS-1:0] sche_in_a_addresss_i`
- `input [`MASK_BITS-1:0] sche_in_a_mask_i`
- `input [`DATA_BITS-1:0] sche_in_a_data_i`
- `input [`PARAM_BITS-1:0] sche_in_a_param_i`
- `output [1] sche_in_d_valid_o`
- `input [1] sche_in_d_ready_i`
- `output [`ADDRESS_BITS-1:0] sche_in_d_address_o`
- `output [`OP_BITS-1:0] sche_in_d_opcode_o`
- `output [`SIZE_BITS-1:0] sche_in_d_size_o`
- `output [`SOURCE_BITS-1:0] sche_in_d_source_o`
- `output [`DATA_BITS-1:0] sche_in_d_data_o`
- `output [`PARAM_BITS-1:0] sche_in_d_param_o`
- `output [1] finish_issue_o`
- `output [1] sche_out_a_valid_o`
- `input [1] sche_out_a_ready_i`
- `output [`OP_BITS-1:0] sche_out_a_opcode_o`
- `output [`SIZE_BITS-1:0] sche_out_a_size_o`
- `output [`SOURCE_BITS-1:0] sche_out_a_source_o`
- `output [`ADDRESS_BITS-1:0] sche_out_a_addresss_o`
- `output [`MASK_BITS-1:0] sche_out_a_mask_o`
- `output [`DATA_BITS-1:0] sche_out_a_data_o`
- `output [`PARAM_BITS-1:0] sche_out_a_param_o`
- `input [1] sche_out_d_valid_i`
- `output [1] sche_out_d_ready_o`
- `input [`OP_BITS-1:0] sche_out_d_opcode_i`
- `input [`SOURCE_BITS-1:0] sche_out_d_source_i`
- `input [`DATA_BITS-1:0] sche_out_d_data_i`

## Submodule Instances
- `U0_one2bin`
- `SRAM`
- `U1_one2bin`
- `U2_one2bin`

## Logic Block Types
- comb
- seq_async_reset
