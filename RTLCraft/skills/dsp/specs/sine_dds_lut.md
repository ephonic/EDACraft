# sine_dds_lut

## Parameters
- `OUTPUT_WIDTH = 16`
- `INPUT_WIDTH = OUTPUT_WIDTH+2`

## Ports (9)
- `input [1] clk`
- `input [1] rst`
- `input [INPUT_WIDTH-1:0] input_phase_tdata`
- `input [1] input_phase_tvalid`
- `output [1] input_phase_tready`
- `output [OUTPUT_WIDTH-1:0] output_sample_i_tdata`
- `output [OUTPUT_WIDTH-1:0] output_sample_q_tdata`
- `output [1] output_sample_tvalid`
- `input [1] output_sample_tready`

## Logic Block Types
- seq
