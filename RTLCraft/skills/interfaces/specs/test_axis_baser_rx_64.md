# test_axis_baser_rx_64

## Parameters
- `DATA_WIDTH = 64`
- `KEEP_WIDTH = (DATA_WIDTH/8)`
- `HDR_WIDTH = 2`
- `PTP_PERIOD_NS = 4'h6`
- `PTP_PERIOD_FNS = 16'h6666`
- `PTP_TS_ENABLE = 0`
- `PTP_TS_WIDTH = 96`
- `USER_WIDTH = (PTP_TS_ENABLE ? PTP_TS_WIDTH : 0) + 1`

## Submodule Instances
- `UUT`
