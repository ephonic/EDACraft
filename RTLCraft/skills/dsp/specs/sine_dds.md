# sine_dds

## Parameters
- `PHASE_WIDTH = 32`
- `OUTPUT_WIDTH = 16`
- `INITIAL_PHASE = 0`
- `INITIAL_PHASE_STEP = 0`

## Ports (12)
- `input [1] clk`
- `input [1] rst`
- `input [PHASE_WIDTH-1:0] input_phase_tdata`
- `input [1] input_phase_tvalid`
- `output [1] input_phase_tready`
- `input [PHASE_WIDTH-1:0] input_phase_step_tdata`
- `input [1] input_phase_step_tvalid`
- `output [1] input_phase_step_tready`
- `output [OUTPUT_WIDTH-1:0] output_sample_i_tdata`
- `output [OUTPUT_WIDTH-1:0] output_sample_q_tdata`
- `output [1] output_sample_tvalid`
- `input [1] output_sample_tready`
