# axis_arb_mux

## Parameters
- `S_COUNT = 4`
- `DATA_WIDTH = 8`
- `KEEP_ENABLE = (DATA_WIDTH>8)`
- `KEEP_WIDTH = ((DATA_WIDTH+7)/8)`
- `ID_ENABLE = 0`
- `S_ID_WIDTH = 8`
- `M_ID_WIDTH = S_ID_WIDTH+$clog2(S_COUNT)`
- `DEST_ENABLE = 0`
- `DEST_WIDTH = 8`
- `USER_ENABLE = 1`
- `USER_WIDTH = 1`
- `LAST_ENABLE = 1`
- `UPDATE_TID = 0`
- `ARB_TYPE_ROUND_ROBIN = 0`
- `ARB_LSB_HIGH_PRIORITY = 1`
- `CL_S_COUNT = $clog2(S_COUNT)`
- `S_ID_WIDTH_INT = S_ID_WIDTH > 0 ? S_ID_WIDTH : 1`

## Logic Block Types
- seq
