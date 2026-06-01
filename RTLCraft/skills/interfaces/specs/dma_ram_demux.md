# dma_ram_demux

## Parameters
- `PORTS = 2`
- `SEG_COUNT = 2`
- `SEG_DATA_WIDTH = 64`
- `SEG_BE_WIDTH = SEG_DATA_WIDTH/8`
- `SEG_ADDR_WIDTH = 8`
- `S_RAM_SEL_WIDTH = 2`
- `M_RAM_SEL_WIDTH = S_RAM_SEL_WIDTH+$clog2(PORTS)`
