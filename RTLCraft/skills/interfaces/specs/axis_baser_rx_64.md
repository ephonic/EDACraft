# axis_baser_rx_64

## Parameters
- `DATA_WIDTH = 64`
- `KEEP_WIDTH = (DATA_WIDTH/8)`
- `HDR_WIDTH = 2`
- `PTP_TS_ENABLE = 0`
- `PTP_TS_FMT_TOD = 1`
- `PTP_TS_WIDTH = PTP_TS_FMT_TOD ? 96 : 64`
- `USER_WIDTH = (PTP_TS_ENABLE ? PTP_TS_WIDTH : 0) + 1`

## Logic Block Types
- seq
