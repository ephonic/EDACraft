# ptp_td_leaf

## Parameters
- `TS_REL_EN = 1`
- `TS_TOD_EN = 1`
- `TS_FNS_W = 16`
- `TS_REL_NS_W = 48`
- `TS_TOD_S_W = 48`
- `TS_REL_W = TS_REL_NS_W + TS_FNS_W`
- `TS_TOD_W = TS_TOD_S_W + 32 + TS_FNS_W`
- `TD_SDI_PIPELINE = 2`

## Ports (13)
- `input [1] clk`
- `input [1] rst`
- `input [1] sample_clk`
- `input [1] ptp_clk`
- `input [1] ptp_rst`
- `input [1] ptp_td_sdi`
- `output [TS_REL_W-1:0] output_ts_rel`
- `output [1] output_ts_rel_step`
- `output [TS_TOD_W-1:0] output_ts_tod`
- `output [1] output_ts_tod_step`
- `output [1] output_pps`
- `output [1] output_pps_str`
- `output [1] locked`

## FSM States
- `PERIOD_NS_W` = 0
- `FNS_W` = 1
- `CMP_FNS_W` = 2
- `LOG_RATE` = 3
- `LOAD_CNT_W` = 4
- `LOG_SAMPLE_SYNC_RATE` = 5
- `LOG_PHASE_ERR_RATE` = 6
- `DST_SYNC_LOCK_W` = 7
- `FREQ_LOCK_W` = 8
- `PTP_LOCK_W` = 9

## Logic Block Types
- seq
