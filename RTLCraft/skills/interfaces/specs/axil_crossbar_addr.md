# axil_crossbar_addr

## Parameters
- `S = 0`
- `S_COUNT = 4`
- `M_COUNT = 4`
- `ADDR_WIDTH = 32`
- `M_REGIONS = 1`
- `M_BASE_ADDR = 0`
- `M_ADDR_WIDTH = {M_COUNT{{M_REGIONS{32'd24}}}}`
- `M_CONNECT = {M_COUNT{{S_COUNT{1'b1}}}}`
- `M_SECURE = {M_COUNT{1'b0}}`
- `WC_OUTPUT = 0`
- `CL_S_COUNT = $clog2(S_COUNT)`
- `CL_M_COUNT = $clog2(M_COUNT)`
- `M_BASE_ADDR_INT = M_BASE_ADDR ? M_BASE_ADDR : calcBaseAddrs(0)`

## Ports (7)
- `input [1] clk`
- `input [1] rst`
- `input [ADDR_WIDTH-1:0] s_axil_aaddr`
- `input [2:0] s_axil_aprot`
- `input [1] s_axil_avalid`
- `output [1] s_axil_aready`
- `output [1] wire`

## Logic Block Types
- seq
