# lfsr

## Parameters
- `LFSR_WIDTH = 31`
- `LFSR_POLY = 31'h10000001`
- `LFSR_CONFIG = "FIBONACCI"`
- `LFSR_FEED_FORWARD = 0`
- `REVERSE = 0`
- `DATA_WIDTH = 8`
- `STYLE = "AUTO"`
- `STYLE_INT = (STYLE == "AUTO") ? "REDUCTION" : STYLE`
- `STYLE_INT = (STYLE == "AUTO") ? "LOOP" : STYLE`

## Ports (4)
- `input [DATA_WIDTH-1:0] data_in`
- `input [LFSR_WIDTH-1:0] state_in`
- `output [DATA_WIDTH-1:0] data_out`
- `output [LFSR_WIDTH-1:0] state_out`
