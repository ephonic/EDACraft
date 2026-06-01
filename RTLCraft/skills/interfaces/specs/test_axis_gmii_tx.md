# test_axis_gmii_tx

## Parameters
- `DATA_WIDTH = 8`
- `ENABLE_PADDING = 1`
- `MIN_FRAME_LENGTH = 64`
- `PTP_TS_ENABLE = 0`
- `PTP_TS_WIDTH = 96`
- `PTP_TAG_ENABLE = PTP_TS_ENABLE`
- `PTP_TAG_WIDTH = 16`
- `USER_WIDTH = (PTP_TAG_ENABLE ? PTP_TAG_WIDTH : 0) + 1`

## Submodule Instances
- `UUT`
