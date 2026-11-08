# Python driver

The driver calls `ftimer` as a separate process and parses timing and power
results. Python 3.9 or newer is required. After building from the EDACraft root:

```sh
export FTIMER_BIN="$PWD/build/ftimer/bin/ftimer"
export PYTHONPATH="$PWD/FTimer/python${PYTHONPATH:+:$PYTHONPATH}"
python3 FTimer/examples/simple/run.py
python3 FTimer/examples/power/run.py
```

An installed tree provides `env.sh`, which sets the executable path and module
search path. You can also pass `executable="/path/to/ftimer"` to `FTimer`.

## Define constraints

```python
from ftimer import FTimer, SDC, get_ports

sdc = SDC()  # ns and pF
sdc.create_clock("clk", 1.25, get_ports("clk"))
sdc.set_input_delay(0.10, get_ports(["a", "b"]), clock="clk")
sdc.set_output_delay(0.15, get_ports("z"), clock="clk")
sdc.set_input_transition(0.02, get_ports(["a", "b"]))
sdc.set_load(0.01, get_ports("z"))
sdc.set_clock_uncertainty(0.03, "clk", analysis="setup")

timer = FTimer(liberty="cells.lib", verilog="design.v",
               spef="design.spef", constraints=sdc)
print(timer.report_timing(max_paths=10, min_paths=10))
timer.write_sdc("effective.sdc")
```

`liberty`, `verilog`, `spef` and `sdc` each accept a path or a sequence of paths.
`constraints=SDC()` adds Python-defined constraints after the file inputs.
Selectors include `get_ports`, `get_pins`, `get_clocks`, `all_inputs` and
`all_outputs`. Keep physical clock ports out of data-input delay selections.
The runnable constraint-builder example is
[`examples/python_constraints.py`](examples/python_constraints.py).

## Estimate power

```python
from ftimer import FTimer, SwitchingActivity

timer = FTimer(liberty="cells.lib", verilog="design.v", sdc="design.sdc")
detail = timer.estimate_power_detail(
    1e9, 0.1,
    activities={"a": SwitchingActivity(1e8, 0.5)},
)
print(detail.summary)
print(detail.coverage)
```

The frequency is in Hz. Default activity is both-edge transitions per cycle;
`SwitchingActivity` takes transitions per second and probability of logic one.
`estimate_power_saif` and `estimate_power_vcd` load waveform-derived annotations.
Inspect coverage and match frequency, logic constants and activity assumptions
when comparing results across tools. The full synthetic power example is
[`../examples/power/run.py`](../examples/power/run.py).

Available query methods and result types are documented in
[`ftimer.py`](ftimer.py); constraint methods are in [`ftimer_sdc.py`](ftimer_sdc.py).
