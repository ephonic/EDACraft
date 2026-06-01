# l2_distribute

## Ports (34)
- `input [1] mem_req_in_valid_i`
- `output [1] mem_req_in_ready_o`
- `input [`OP_BITS-1:0] mem_req_in_opcode_i`
- `input [`SIZE_BITS-1:0] mem_req_in_size_i`
- `input [`CLUSTER_SOURCE-1:0] mem_req_in_source_i`
- `input [`ADDRESS_BITS-1:0] mem_req_in_address_i`
- `input [`MASK_BITS-1:0] mem_req_in_mask_i`
- `input [`DATA_BITS-1:0] mem_req_in_data_i`
- `input [2:0] mem_req_in_param_i`
- `output [`NUM_L2CACHE-1:0] mem_req_vec_out_valid_o`
- `input [`NUM_L2CACHE-1:0] mem_req_vec_out_ready_i`
- `output [`NUM_L2CACHE*`OP_BITS-1:0] mem_req_vec_out_opcode_o`
- `output [`NUM_L2CACHE*`SIZE_BITS-1:0] mem_req_vec_out_size_o`
- `output [`NUM_L2CACHE*`CLUSTER_SOURCE-1:0] mem_req_vec_out_source_o`
- `output [`NUM_L2CACHE*`ADDRESS_BITS-1:0] mem_req_vec_out_address_o`
- `output [`NUM_L2CACHE*`MASK_BITS-1:0] mem_req_vec_out_mask_o`
- `output [`NUM_L2CACHE*`DATA_BITS-1:0] mem_req_vec_out_data_o`
- `output [`NUM_L2CACHE*3-1:0] mem_req_vec_out_param_o`
- `input [`NUM_L2CACHE-1:0] mem_rsp_vec_in_valid_i`
- `output [`NUM_L2CACHE-1:0] mem_rsp_vec_in_ready_o`
- `input [`NUM_L2CACHE*`ADDRESS_BITS-1:0] mem_rsp_vec_in_address_i`
- `input [`NUM_L2CACHE*`OP_BITS-1:0] mem_rsp_vec_in_opcode_i`
- `input [`NUM_L2CACHE*`SIZE_BITS-1:0] mem_rsp_vec_in_size_i`
- `input [`NUM_L2CACHE*`CLUSTER_SOURCE-1:0] mem_rsp_vec_in_source_i`
- `input [`NUM_L2CACHE*`DATA_BITS-1:0] mem_rsp_vec_in_data_i`
- `input [`NUM_L2CACHE*3-1:0] mem_rsp_vec_in_param_i`
- `output [1] mem_rsp_out_valid_o`
- `input [1] mem_rsp_out_ready_i`
- `output [`ADDRESS_BITS-1:0] mem_rsp_out_address_o`
- `output [`OP_BITS-1:0] mem_rsp_out_opcode_o`
- `output [`SIZE_BITS-1:0] mem_rsp_out_size_o`
- `output [`CLUSTER_SOURCE-1:0] mem_rsp_out_source_o`
- `output [`DATA_BITS-1:0] mem_rsp_out_data_o`
- `output [2:0] mem_rsp_out_param_o`

## Submodule Instances
- `U_one2bin`
