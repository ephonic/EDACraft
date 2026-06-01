# axil_crossbar_rd

## Parameters
- `S_COUNT = 4`
- `M_COUNT = 4`
- `DATA_WIDTH = 32`
- `ADDR_WIDTH = 32`
- `STRB_WIDTH = (DATA_WIDTH/8)`
- `S_ACCEPT = {S_COUNT{32'd16}}`
- `M_REGIONS = 1`
- `M_BASE_ADDR = 0`
- `M_ADDR_WIDTH = {M_COUNT{{M_REGIONS{32'd24}}}}`
- `M_CONNECT = {M_COUNT{{S_COUNT{1'b1}}}}`
- `M_ISSUE = {M_COUNT{32'd16}}`
- `M_SECURE = {M_COUNT{1'b0}}`
- `S_AR_REG_TYPE = {S_COUNT{2'd0}}`
- `S_R_REG_TYPE = {S_COUNT{2'd2}}`
- `M_AR_REG_TYPE = {M_COUNT{2'd1}}`
- `M_R_REG_TYPE = {M_COUNT{2'd0}}`
- `CL_S_COUNT = $clog2(S_COUNT)`
- `CL_M_COUNT = $clog2(M_COUNT)`
- `M_COUNT_P1 = M_COUNT+1`
- `CL_M_COUNT_P1 = $clog2(M_COUNT_P1)`

## Logic Block Types
- seq
