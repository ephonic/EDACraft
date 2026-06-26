# gfsk_modulation

## Parameters
- `SAMPLE_PER_SYMBOL = 8`
- `GAUSS_FILTER_BIT_WIDTH = 16`
- `NUM_TAP_GAUSS_FILTER = 17`
- `VCO_BIT_WIDTH = 16`
- `SIN_COS_ADDR_BIT_WIDTH = 11`
- `IQ_BIT_WIDTH = 8`
- `GAUSS_FIR_OUT_AMP_SCALE_DOWN_NUM_BIT_SHIFT = 1`

## Ports (4)
- `input [1] clk`
- `input [1] rst`
- `input [3:0] gauss_filter_tap_index`
- `input [1] signed`
