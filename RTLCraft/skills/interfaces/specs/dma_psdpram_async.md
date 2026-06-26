# dma_psdpram_async

## Parameters
- `SIZE = 4096`
- `SEG_COUNT = 2`
- `SEG_DATA_WIDTH = 128`
- `SEG_BE_WIDTH = SEG_DATA_WIDTH/8`
- `SEG_ADDR_WIDTH = $clog2(SIZE/(SEG_COUNT*SEG_BE_WIDTH))`
- `PIPELINE = 2`
- `INT_ADDR_WIDTH = $clog2(SIZE/(SEG_COUNT*SEG_BE_WIDTH))`

## Logic Block Types
- seq
