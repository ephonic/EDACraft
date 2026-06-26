# test_axis_async_frame_fifo_64

## Parameters
- `DEPTH = 512`
- `DATA_WIDTH = 64`
- `KEEP_ENABLE = (DATA_WIDTH>8)`
- `KEEP_WIDTH = (DATA_WIDTH/8)`
- `LAST_ENABLE = 1`
- `ID_ENABLE = 1`
- `ID_WIDTH = 8`
- `DEST_ENABLE = 1`
- `DEST_WIDTH = 8`
- `USER_ENABLE = 1`
- `USER_WIDTH = 1`
- `PIPELINE_OUTPUT = 2`
- `FRAME_FIFO = 1`
- `USER_BAD_FRAME_VALUE = 1'b1`
- `USER_BAD_FRAME_MASK = 1'b1`
- `DROP_BAD_FRAME = 1`
- `DROP_WHEN_FULL = 0`

## Submodule Instances
- `UUT`
