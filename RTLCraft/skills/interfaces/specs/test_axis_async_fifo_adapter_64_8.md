# test_axis_async_fifo_adapter_64_8

## Parameters
- `DEPTH = 32`
- `S_DATA_WIDTH = 64`
- `S_KEEP_ENABLE = (S_DATA_WIDTH>8)`
- `S_KEEP_WIDTH = (S_DATA_WIDTH/8)`
- `M_DATA_WIDTH = 8`
- `M_KEEP_ENABLE = (M_DATA_WIDTH>8)`
- `M_KEEP_WIDTH = (M_DATA_WIDTH/8)`
- `ID_ENABLE = 1`
- `ID_WIDTH = 8`
- `DEST_ENABLE = 1`
- `DEST_WIDTH = 8`
- `USER_ENABLE = 1`
- `USER_WIDTH = 1`
- `PIPELINE_OUTPUT = 2`
- `FRAME_FIFO = 0`
- `USER_BAD_FRAME_VALUE = 1'b1`
- `USER_BAD_FRAME_MASK = 1'b1`
- `DROP_BAD_FRAME = 0`
- `DROP_WHEN_FULL = 0`

## Submodule Instances
- `UUT`
