# test_axi_interconnect_4x4

## Parameters
- `S_COUNT = 4`
- `M_COUNT = 4`
- `DATA_WIDTH = 32`
- `ADDR_WIDTH = 32`
- `STRB_WIDTH = (DATA_WIDTH/8)`
- `ID_WIDTH = 8`
- `AWUSER_ENABLE = 0`
- `AWUSER_WIDTH = 1`
- `WUSER_ENABLE = 0`
- `WUSER_WIDTH = 1`
- `BUSER_ENABLE = 0`
- `BUSER_WIDTH = 1`
- `ARUSER_ENABLE = 0`
- `ARUSER_WIDTH = 1`
- `RUSER_ENABLE = 0`
- `RUSER_WIDTH = 1`
- `FORWARD_ID = 1`
- `M_REGIONS = 1`
- `M_BASE_ADDR = {32'h03000000`
- `M_ADDR_WIDTH = {M_COUNT{{M_REGIONS{32'd24}}}}`
- `M_CONNECT_READ = {M_COUNT{{S_COUNT{1'b1}}}}`
- `M_CONNECT_WRITE = {M_COUNT{{S_COUNT{1'b1}}}}`
- `M_SECURE = {M_COUNT{1'b0}}`

## Submodule Instances
- `UUT`
