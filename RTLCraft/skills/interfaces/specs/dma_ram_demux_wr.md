# dma_ram_demux_wr

## Parameters
- `PORTS = 2`
- `SEG_COUNT = 2`
- `SEG_DATA_WIDTH = 64`
- `SEG_BE_WIDTH = SEG_DATA_WIDTH/8`
- `SEG_ADDR_WIDTH = 8`
- `S_RAM_SEL_WIDTH = 2`
- `M_RAM_SEL_WIDTH = S_RAM_SEL_WIDTH+$clog2(PORTS)`
- `CL_PORTS = $clog2(PORTS)`
- `S_RAM_SEL_WIDTH_INT = S_RAM_SEL_WIDTH > 0 ? S_RAM_SEL_WIDTH : 1`
- `FIFO_ADDR_WIDTH = 5`

## Logic Block Types
- seq
