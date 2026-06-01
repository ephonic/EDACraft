# axis2avst

## Parameters
- `DATA_WIDTH = 8`
- `KEEP_WIDTH = (DATA_WIDTH/8)`
- `KEEP_ENABLE = (DATA_WIDTH>8)`
- `EMPTY_WIDTH = $clog2(KEEP_WIDTH)`
- `BYTE_REVERSE = 0`
- `BYTE_WIDTH = KEEP_ENABLE ? DATA_WIDTH / KEEP_WIDTH : DATA_WIDTH`

## Logic Block Types
- seq
