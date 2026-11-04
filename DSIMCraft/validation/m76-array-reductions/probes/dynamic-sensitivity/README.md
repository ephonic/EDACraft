# Dynamic array implicit sensitivity difference

`input.sv` is the unmodified first timing fixture. VCS W-2024.09 reports
`09` for dynamic_sum after subsequent element writes, self-growth and delete.
dsim reports `19`, `20`, `00`, tracking descriptor content changes. These raw
logs/VCD are retained as a difference, not as an alignment pass.

`tests/array_reductions/native-only/dynamic_sensitivity.sv` keeps this input and
checks the dsim results across backends/formats and failed-prediction replay.
The shared timing fixture adds a scalar refresh dependency after each mutation;
its accepted VCS evidence lives in `../../vcs/timing/`. No VCS observation is
excluded to hide the original difference.
