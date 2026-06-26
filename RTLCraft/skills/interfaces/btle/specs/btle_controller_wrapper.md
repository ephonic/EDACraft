# btle_controller_wrapper

## Parameters
- `CLK_FREQUENCE = 16_000_000`
- `BAUD_RATE = 115200`
- `PARITY = "NONE"`
- `FRAME_WD = 8`
- `CRC_STATE_BIT_WIDTH = 24`
- `CHANNEL_NUMBER_BIT_WIDTH = 6`
- `SAMPLE_PER_SYMBOL = 8`
- `GAUSS_FILTER_BIT_WIDTH = 16`
- `NUM_TAP_GAUSS_FILTER = 17`
- `VCO_BIT_WIDTH = 16`
- `SIN_COS_ADDR_BIT_WIDTH = 11`
- `IQ_BIT_WIDTH = 8`
- `GAUSS_FIR_OUT_AMP_SCALE_DOWN_NUM_BIT_SHIFT = 1`
- `GFSK_DEMODULATION_BIT_WIDTH = 16`
- `LEN_UNIQUE_BIT_SEQUENCE = 32`

## Ports (6)
- `input [1] clk`
- `input [1] rst`
- `input [1] clkb`
- `input [1] uart_rx`
- `output [1] uart_tx`
- `output [1] signed`

## Logic Block Types
- seq
