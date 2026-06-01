# ptp_td_rel2tod

## Parameters
- `TS_FNS_W = 16`
- `TS_REL_NS_W = 32`
- `TS_TOD_S_W = 48`
- `TS_REL_W = TS_REL_NS_W + TS_FNS_W`
- `TS_TOD_W = TS_TOD_S_W + 32 + TS_FNS_W`
- `TS_TAG_W = 8`
- `TD_SDI_PIPELINE = 2`

## Ports (11)
- `input [1] clk`
- `input [1] rst`
- `input [1] ptp_clk`
- `input [1] ptp_rst`
- `input [1] ptp_td_sdi`
- `input [TS_REL_W-1:0] input_ts_rel`
- `input [TS_TAG_W-1:0] input_ts_tag`
- `input [1] input_ts_valid`
- `output [TS_TOD_W-1:0] output_ts_tod`
- `output [TS_TAG_W-1:0] output_ts_tag`
- `output [1] output_ts_valid`

## Logic Block Types
- seq
