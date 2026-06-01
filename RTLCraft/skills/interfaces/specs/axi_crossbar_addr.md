# axi_crossbar_addr

## Parameters
- `S = 0`
- `S_COUNT = 4`
- `M_COUNT = 4`
- `ADDR_WIDTH = 32`
- `ID_WIDTH = 8`
- `S_THREADS = 32'd2`
- `S_ACCEPT = 32'd16`
- `M_REGIONS = 1`
- `M_BASE_ADDR = 0`
- `M_ADDR_WIDTH = {M_COUNT{{M_REGIONS{32'd24}}}}`
- `M_CONNECT = {M_COUNT{{S_COUNT{1'b1}}}}`
- `M_SECURE = {M_COUNT{1'b0}}`
- `WC_OUTPUT = 0`
- `CL_S_COUNT = $clog2(S_COUNT)`
- `CL_M_COUNT = $clog2(M_COUNT)`
- `S_INT_THREADS = S_THREADS > S_ACCEPT ? S_ACCEPT : S_THREADS`
- `CL_S_INT_THREADS = $clog2(S_INT_THREADS)`
- `CL_S_ACCEPT = $clog2(S_ACCEPT)`
- `M_BASE_ADDR_INT = M_BASE_ADDR ? M_BASE_ADDR : calcBaseAddrs(0)`

## Ports (10)
- `input [1] clk`
- `input [1] rst`
- `input [ID_WIDTH-1:0] s_axi_aid`
- `input [ADDR_WIDTH-1:0] s_axi_aaddr`
- `input [2:0] s_axi_aprot`
- `input [3:0] s_axi_aqos`
- `input [1] s_axi_avalid`
- `output [1] s_axi_aready`
- `output [3:0] m_axi_aregion`
- `output [1] wire`

## Logic Block Types
- seq
