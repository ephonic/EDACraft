# pcie_us_cfg

## Parameters
- `PF_COUNT = 1`
- `VF_COUNT = 0`
- `VF_OFFSET = 64`
- `F_COUNT = PF_COUNT+VF_COUNT`
- `READ_EXT_TAG_ENABLE = 1`
- `READ_MAX_READ_REQ_SIZE = 1`
- `READ_MAX_PAYLOAD_SIZE = 1`
- `PCIE_CAP_OFFSET = 12'h0C0`

## Ports (13)
- `input [1] clk`
- `input [1] rst`
- `output [F_COUNT-1:0] ext_tag_enable`
- `output [F_COUNT*3-1:0] max_read_request_size`
- `output [F_COUNT*3-1:0] max_payload_size`
- `output [9:0] cfg_mgmt_addr`
- `output [7:0] cfg_mgmt_function_number`
- `output [1] cfg_mgmt_write`
- `output [31:0] cfg_mgmt_write_data`
- `output [3:0] cfg_mgmt_byte_enable`
- `output [1] cfg_mgmt_read`
- `input [31:0] cfg_mgmt_read_data`
- `input [1] cfg_mgmt_read_write_done`

## Logic Block Types
- seq
