# axis_pipeline_fifo

## Parameters
- `DATA_WIDTH = 8`
- `KEEP_ENABLE = (DATA_WIDTH>8)`
- `KEEP_WIDTH = ((DATA_WIDTH+7)/8)`
- `LAST_ENABLE = 1`
- `ID_ENABLE = 0`
- `ID_WIDTH = 8`
- `DEST_ENABLE = 0`
- `DEST_WIDTH = 8`
- `USER_ENABLE = 1`
- `USER_WIDTH = 1`
- `LENGTH = 2`
- `FIFO_ADDR_WIDTH = LENGTH < 2 ? 3 : $clog2(LENGTH*4+1)`

## Logic Block Types
- seq
