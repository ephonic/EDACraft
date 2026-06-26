# ptp_td_phc

## Parameters
- `PERIOD_NS_NUM = 32`
- `PERIOD_NS_DENOM = 5`

## Ports (29)
- `input [1] clk`
- `input [1] rst`
- `input [47:0] input_ts_tod_s`
- `input [29:0] input_ts_tod_ns`
- `input [1] input_ts_tod_valid`
- `output [1] input_ts_tod_ready`
- `input [29:0] input_ts_tod_offset_ns`
- `input [1] input_ts_tod_offset_valid`
- `output [1] input_ts_tod_offset_ready`
- `input [47:0] input_ts_rel_ns`
- `input [1] input_ts_rel_valid`
- `output [1] input_ts_rel_ready`
- `input [31:0] input_ts_rel_offset_ns`
- `input [1] input_ts_rel_offset_valid`
- `output [1] input_ts_rel_offset_ready`
- `input [31:0] input_ts_offset_fns`
- `input [1] input_ts_offset_valid`
- `output [1] input_ts_offset_ready`
- `input [7:0] input_period_ns`
- `input [31:0] input_period_fns`
- `input [1] input_period_valid`
- `output [1] input_period_ready`
- `input [15:0] input_drift_num`
- `input [15:0] input_drift_denom`
- `input [1] input_drift_valid`
- `output [1] input_drift_ready`
- `output [1] ptp_td_sdo`
- `output [1] output_pps`
- `output [1] output_pps_str`

## FSM States
- `INC_NS_W` = 0

## Logic Block Types
- seq
