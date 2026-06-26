# ptp_perout

## Parameters
- `FNS_ENABLE = 1`
- `OUT_START_S = 48'h0`
- `OUT_START_NS = 30'h0`
- `OUT_START_FNS = 16'h0000`
- `OUT_PERIOD_S = 48'd1`
- `OUT_PERIOD_NS = 30'd0`
- `OUT_PERIOD_FNS = 16'h0000`
- `OUT_WIDTH_S = 48'h0`
- `OUT_WIDTH_NS = 30'd1000`
- `OUT_WIDTH_FNS = 16'h0000`

## Ports (14)
- `input [1] clk`
- `input [1] rst`
- `input [95:0] input_ts_96`
- `input [1] input_ts_step`
- `input [1] enable`
- `input [95:0] input_start`
- `input [1] input_start_valid`
- `input [95:0] input_period`
- `input [1] input_period_valid`
- `input [95:0] input_width`
- `input [1] input_width_valid`
- `output [1] locked`
- `output [1] error`
- `output [1] output_pulse`

## Logic Block Types
- seq
