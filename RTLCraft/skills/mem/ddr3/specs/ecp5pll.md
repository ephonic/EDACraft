# ecp5pll

## Parameters
- `in_hz = 25000000`
- `out0_hz = 25000000`
- `out0_deg = 0`
- `out0_tol_hz = 0`
- `out1_hz = 0`
- `out1_deg = 0`
- `out1_tol_hz = 0`
- `out2_hz = 0`
- `out2_deg = 0`
- `out2_tol_hz = 0`
- `out3_hz = 0`
- `out3_deg = 0`
- `out3_tol_hz = 0`
- `reset_en = 0`
- `standby_en = 0`
- `dynamic_en = 0`

## Ports (7)
- `input [1] clk_i`
- `output [3:0] clk_o`
- `input [1] reset`
- `input [1] standby`
- `input [1:0] phasesel`
- `input [1] phasedir`
- `output [1] locked`

## Submodule Instances
- `EHXPLLL`
