# ptp_clock

## Parameters
- `PERIOD_NS_WIDTH = 4`
- `OFFSET_NS_WIDTH = 4`
- `DRIFT_NS_WIDTH = 4`
- `FNS_WIDTH = 16`
- `PERIOD_NS = 4'h6`
- `PERIOD_FNS = 16'h6666`
- `DRIFT_ENABLE = 1`
- `DRIFT_NS = 4'h0`
- `DRIFT_FNS = 16'h0002`
- `DRIFT_RATE = 16'h0005`
- `PIPELINE_OUTPUT = 0`
- `INC_NS_WIDTH = $clog2(2**PERIOD_NS_WIDTH + 2**OFFSET_NS_WIDTH + 2**DRIFT_NS_WIDTH)`

## Ports (22)
- `input [1] clk`
- `input [1] rst`
- `input [95:0] input_ts_96`
- `input [1] input_ts_96_valid`
- `input [63:0] input_ts_64`
- `input [1] input_ts_64_valid`
- `input [PERIOD_NS_WIDTH-1:0] input_period_ns`
- `input [FNS_WIDTH-1:0] input_period_fns`
- `input [1] input_period_valid`
- `input [OFFSET_NS_WIDTH-1:0] input_adj_ns`
- `input [FNS_WIDTH-1:0] input_adj_fns`
- `input [15:0] input_adj_count`
- `input [1] input_adj_valid`
- `output [1] input_adj_active`
- `input [DRIFT_NS_WIDTH-1:0] input_drift_ns`
- `input [FNS_WIDTH-1:0] input_drift_fns`
- `input [15:0] input_drift_rate`
- `input [1] input_drift_valid`
- `output [95:0] output_ts_96`
- `output [63:0] output_ts_64`
- `output [1] output_ts_step`
- `output [1] output_pps`

## Logic Block Types
- seq
