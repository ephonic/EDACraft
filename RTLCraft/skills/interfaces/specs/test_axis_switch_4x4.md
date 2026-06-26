# test_axis_switch_4x4

## Parameters
- `S_COUNT = 4`
- `M_COUNT = 4`
- `DATA_WIDTH = 8`
- `KEEP_ENABLE = (DATA_WIDTH>8)`
- `KEEP_WIDTH = (DATA_WIDTH/8)`
- `ID_ENABLE = 1`
- `ID_WIDTH = 8`
- `DEST_WIDTH = $clog2(M_COUNT+1)`
- `USER_ENABLE = 1`
- `USER_WIDTH = 1`
- `M_BASE = {3'd3`
- `M_TOP = {3'd3`
- `M_CONNECT = {M_COUNT{{S_COUNT{1'b1}}}}`
- `S_REG_TYPE = 0`
- `M_REG_TYPE = 2`
- `ARB_TYPE_ROUND_ROBIN = 1`
- `ARB_LSB_HIGH_PRIORITY = 1`

## Submodule Instances
- `UUT`
