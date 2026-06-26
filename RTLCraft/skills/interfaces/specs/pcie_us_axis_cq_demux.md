# pcie_us_axis_cq_demux

## Parameters
- `M_COUNT = 2`
- `AXIS_PCIE_DATA_WIDTH = 256`
- `AXIS_PCIE_KEEP_WIDTH = (AXIS_PCIE_DATA_WIDTH/32)`
- `AXIS_PCIE_CQ_USER_WIDTH = AXIS_PCIE_DATA_WIDTH < 512 ? 85 : 183`
- `CL_M_COUNT = $clog2(M_COUNT)`

## Logic Block Types
- seq
