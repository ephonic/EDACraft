# axil_interconnect

## Parameters
- `S_COUNT = 4`
- `M_COUNT = 4`
- `DATA_WIDTH = 32`
- `ADDR_WIDTH = 32`
- `STRB_WIDTH = (DATA_WIDTH/8)`
- `M_REGIONS = 1`
- `M_BASE_ADDR = 0`
- `M_ADDR_WIDTH = {M_COUNT{{M_REGIONS{32'd24}}}}`
- `M_CONNECT_READ = {M_COUNT{{S_COUNT{1'b1}}}}`
- `M_CONNECT_WRITE = {M_COUNT{{S_COUNT{1'b1}}}}`
- `M_SECURE = {M_COUNT{1'b0}}`
- `CL_S_COUNT = $clog2(S_COUNT)`
- `CL_M_COUNT = $clog2(M_COUNT)`
- `M_BASE_ADDR_INT = M_BASE_ADDR ? M_BASE_ADDR : calcBaseAddrs(0)`

## Logic Block Types
- seq
