# axil_dp_ram

## Parameters
- `DATA_WIDTH = 32`
- `ADDR_WIDTH = 16`
- `STRB_WIDTH = (DATA_WIDTH/8)`
- `PIPELINE_OUTPUT = 0`
- `VALID_ADDR_WIDTH = ADDR_WIDTH - $clog2(STRB_WIDTH)`
- `WORD_WIDTH = STRB_WIDTH`
- `WORD_SIZE = DATA_WIDTH/WORD_WIDTH`

## Logic Block Types
- seq
