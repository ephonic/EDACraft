# TwiddleConvert4

## Parameters
- `LOG_N = 6`
- `WIDTH = 16`
- `TW_FF = 1`
- `TC_FF = 1`

## Ports (7)
- `input [1] clock`
- `input [LOG_N-1:0] tw_addr`
- `input [WIDTH-1:0] tw_re`
- `input [WIDTH-1:0] tw_im`
- `output [LOG_N-1:0] tc_addr`
- `output [WIDTH-1:0] tc_re`
- `output [WIDTH-1:0] tc_im`

## Logic Block Types
- seq
