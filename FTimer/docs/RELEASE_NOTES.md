# Release 0.1.1 — 2026-11-08

- Publish a standalone source layout with the shared model embedded under
  `src/core` and `include/edacraft`.
- Synchronize the timer headers, implementation, power analysis and coupled-RC/
  CCSN solver work used by the development `ftimer_craft` and fsyn integration.
- Retain the source-grid and active/quiet waveform fixes verified during the
  RC/HSPICE comparison work.
- Correct power-detail activity for electrically merged wire aliases, preserving
  zero additional capacitance and power on alias-only records.
- Export an installable CMake SDK and provide synthetic CLI, Python timing/power
  and C++ consumer examples.
- Fold CLI/tools into `src` and keep the principal source directories in this
  public snapshot. Development reports, test archives and compiled installations
  remain outside the published tree.

The 4.83% linear RC versus PrimeTime D-branch investigation is closed. Its
measured discrepancy remains recorded; the solver is retained based on the
independent HSPICE/analytical evidence. See [validation](VALIDATION.md) for the
remaining nonlinear CCSN and full-design SI scope.
