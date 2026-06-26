# ptp_clock_cdc

## Parameters
- `TS_WIDTH = 96`
- `NS_WIDTH = 4`
- `LOG_RATE = 3`
- `PIPELINE_OUTPUT = 0`

## Ports (11)
- `input [1] input_clk`
- `input [1] input_rst`
- `input [1] output_clk`
- `input [1] output_rst`
- `input [1] sample_clk`
- `input [TS_WIDTH-1:0] input_ts`
- `input [1] input_ts_step`
- `output [TS_WIDTH-1:0] output_ts`
- `output [1] output_ts_step`
- `output [1] output_pps`
- `output [1] locked`

## FSM States
- `FNS_WIDTH` = 0
- `CMP_FNS_WIDTH` = 1
- `LOG_PHASE_ERR_RATE` = 2
- `DEST_SYNC_LOCK_WIDTH` = 3
- `FREQ_LOCK_WIDTH` = 4
- `PTP_LOCK_WIDTH` = 5

## Logic Block Types
- seq
