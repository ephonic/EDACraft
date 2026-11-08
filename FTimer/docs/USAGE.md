# Timing and power usage

Supply a mapped gate-level netlist and matching Liberty libraries. FTimer accepts
multiple `-lib` inputs. SDC defines clocks, I/O delays, exceptions, uncertainties,
loads and analysis limits; SPEF supplies extracted resistance and capacitance.

```sh
ftimer -lib cells.lib -verilog design.v -top top -sdc design.sdc \
  -spef design.spef -report 10 -report_min 10
```

`-report` selects setup/max paths; `-report_min` selects hold/min paths. Use
`-query_pin instance/pin`, `-dump_pins` and `-dump_pins_min` to inspect arrivals
and slews. `-check_coverage` reports timing-check coverage, and
`-design_rule_violations` reports resolved electrical-limit violations.

The Python SDC builder uses ns and pF. Library and SPEF input units are parsed
from the corresponding files. Set operating voltage explicitly when required by
the intended analysis configuration.

```sh
ftimer -lib cells.lib -verilog design.v -sdc design.sdc \
  -power 1e9 -activity 0.1 -power_detail \
  -power_activity a 1e8 0.5
```

This uses a 1 GHz reference frequency, default activity of 0.1 both-edge
transitions/cycle, and an explicit annotation of 100 million transitions/second
with P(1)=0.5 on `a`. Power detail includes cells, nets and annotation/propagation
coverage. The Python driver also accepts SAIF and VCD annotations.

For coupling inspection, `-si` prints the SPEF coupling inventory and `-si_detail`
prints normalized victim/aggressor pairs. `-si_victim`, repeatable `-si_aggressor`
and `-si_waveform_file` expose controlled waveform analysis. Use `ftimer -help`
for the exact argument list. Ground-capacitance-only SPEF cannot exercise a
coupled victim/aggressor network; use extracted coupling data for that purpose.

Model availability and analysis settings affect the calculated results. Inspect
coverage and [validation limits](VALIDATION.md) when selecting a flow.
