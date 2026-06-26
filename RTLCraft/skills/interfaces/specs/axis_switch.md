# axis_switch

## Parameters
- `S_COUNT = 4`
- `M_COUNT = 4`
- `DATA_WIDTH = 8`
- `KEEP_ENABLE = (DATA_WIDTH>8)`
- `KEEP_WIDTH = ((DATA_WIDTH+7)/8)`
- `ID_ENABLE = 0`
- `S_ID_WIDTH = 8`
- `M_ID_WIDTH = S_ID_WIDTH+$clog2(S_COUNT)`
- `M_DEST_WIDTH = 1`
- `S_DEST_WIDTH = M_DEST_WIDTH+$clog2(M_COUNT)`
- `USER_ENABLE = 1`
- `USER_WIDTH = 1`
- `M_BASE = 0`
- `M_TOP = 0`
- `M_CONNECT = {M_COUNT{{S_COUNT{1'b1}}}}`
- `UPDATE_TID = 0`
- `S_REG_TYPE = 0`
- `M_REG_TYPE = 2`
- `ARB_TYPE_ROUND_ROBIN = 1`
- `ARB_LSB_HIGH_PRIORITY = 1`
- `CL_S_COUNT = $clog2(S_COUNT)`
- `CL_M_COUNT = $clog2(M_COUNT)`
- `S_ID_WIDTH_INT = S_ID_WIDTH > 0 ? S_ID_WIDTH : 1`
- `M_DEST_WIDTH_INT = M_DEST_WIDTH > 0 ? M_DEST_WIDTH : 1`

## Logic Block Types
- seq
