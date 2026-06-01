# mem_inter

## Parameters
- `META_FNAME_SIZE = 128`
- `METADATA_SIZE = 1024`
- `DATA_FNAME_SIZE = 128`
- `DATADATA_SIZE = 2000`
- `BUF_NUM = 18`
- `MEM_ADDR = 32`

## Ports (18)
- `input [1] clk`
- `input [1] rstn`
- `input [`NUM_L2CACHE-1:0] out_a_valid_o`
- `output [`NUM_L2CACHE-1:0] out_a_ready_i`
- `input [`NUM_L2CACHE*`OP_BITS-1:0] out_a_opcode_o`
- `input [`NUM_L2CACHE*`SIZE_BITS-1:0] out_a_size_o`
- `input [`NUM_L2CACHE*`SOURCE_BITS-1:0] out_a_source_o`
- `input [`NUM_L2CACHE*`ADDRESS_BITS-1:0] out_a_address_o`
- `input [`NUM_L2CACHE*`MASK_BITS-1:0] out_a_mask_o`
- `input [`NUM_L2CACHE*`DATA_BITS-1:0] out_a_data_o`
- `input [`NUM_L2CACHE*3-1:0] out_a_param_o`
- `output [`NUM_L2CACHE-1:0] out_d_valid_i`
- `input [`NUM_L2CACHE-1:0] out_d_ready_o`
- `output [`NUM_L2CACHE*`OP_BITS-1:0] out_d_opcode_i`
- `output [`NUM_L2CACHE*`SIZE_BITS-1:0] out_d_size_i`
- `output [`NUM_L2CACHE*`SOURCE_BITS-1:0] out_d_source_i`
- `output [`NUM_L2CACHE*`DATA_BITS-1:0] out_d_data_i`
- `output [`NUM_L2CACHE*3-1:0] out_d_param_i`
