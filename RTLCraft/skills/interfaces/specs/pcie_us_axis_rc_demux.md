# pcie_us_axis_rc_demux

## Parameters
- `M_COUNT = 2`
- `AXIS_PCIE_DATA_WIDTH = 256`
- `AXIS_PCIE_KEEP_WIDTH = (AXIS_PCIE_DATA_WIDTH/32)`
- `AXIS_PCIE_RC_USER_WIDTH = AXIS_PCIE_DATA_WIDTH < 512 ? 75 : 161`
- `CL_M_COUNT = $clog2(M_COUNT)`

## Logic Block Types
- seq
