# axi_cdma_desc_mux

## Parameters
- `PORTS = 2`
- `AXI_ADDR_WIDTH = 16`
- `LEN_WIDTH = 20`
- `S_TAG_WIDTH = 8`
- `M_TAG_WIDTH = S_TAG_WIDTH+$clog2(PORTS)`
- `ARB_TYPE_ROUND_ROBIN = 1`
- `ARB_LSB_HIGH_PRIORITY = 1`
- `CL_PORTS = $clog2(PORTS)`

## Logic Block Types
- seq
