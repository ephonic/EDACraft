# axis_demux

## Parameters
- `M_COUNT = 4`
- `DATA_WIDTH = 8`
- `KEEP_ENABLE = (DATA_WIDTH>8)`
- `KEEP_WIDTH = ((DATA_WIDTH+7)/8)`
- `ID_ENABLE = 0`
- `ID_WIDTH = 8`
- `DEST_ENABLE = 0`
- `M_DEST_WIDTH = 8`
- `S_DEST_WIDTH = M_DEST_WIDTH+$clog2(M_COUNT)`
- `USER_ENABLE = 1`
- `USER_WIDTH = 1`
- `TDEST_ROUTE = 0`
- `CL_M_COUNT = $clog2(M_COUNT)`
- `M_DEST_WIDTH_INT = M_DEST_WIDTH > 0 ? M_DEST_WIDTH : 1`

## Logic Block Types
- seq
