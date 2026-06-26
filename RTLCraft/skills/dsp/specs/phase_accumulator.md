# phase_accumulator

## Parameters
- `WIDTH = 32`
- `INITIAL_PHASE = 0`
- `INITIAL_PHASE_STEP = 0`

## Ports (11)
- `input [1] clk`
- `input [1] rst`
- `input [WIDTH-1:0] input_phase_tdata`
- `input [1] input_phase_tvalid`
- `output [1] input_phase_tready`
- `input [WIDTH-1:0] input_phase_step_tdata`
- `input [1] input_phase_step_tvalid`
- `output [1] input_phase_step_tready`
- `output [WIDTH-1:0] output_phase_tdata`
- `output [1] output_phase_tvalid`
- `input [1] output_phase_tready`

## Logic Block Types
- seq
