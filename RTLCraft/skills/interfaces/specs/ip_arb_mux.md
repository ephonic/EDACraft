# ip_arb_mux

## Parameters
- `S_COUNT = 4`
- `DATA_WIDTH = 8`
- `KEEP_ENABLE = (DATA_WIDTH>8)`
- `KEEP_WIDTH = (DATA_WIDTH/8)`
- `ID_ENABLE = 0`
- `ID_WIDTH = 8`
- `DEST_ENABLE = 0`
- `DEST_WIDTH = 8`
- `USER_ENABLE = 1`
- `USER_WIDTH = 1`
- `ARB_TYPE_ROUND_ROBIN = 0`
- `ARB_LSB_HIGH_PRIORITY = 1`
- `CL_S_COUNT = $clog2(S_COUNT)`

## Logic Block Types
- seq
