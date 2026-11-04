# M128: rejected static notification candidates

All three candidates specialize subscriptions from static WaitIR connections, preserve registration/FIFO order and four-state edges, and exclude dynamic/multiple waits and complex kernel features. No module names, instruction contents or checksums select an optimization. None is enabled or retained in production.

On Linux CPU 25, identical Intel 2026.1 `-O3 -fp-model=strict -xHost -ipo`, complete unchanged workloads, one warmup and three rotated measured rounds:

- Callback table: CPU 10.18s versus frozen M126 9.32s; CRC 3.17s versus 3.06s.
- Generated direct switch: CPU 9.74s versus 9.32s; CRC 3.38s versus 3.07s.
- Direct switch with forced small-template inlining: CPU samples 10.21/10.28/10.32s versus 9.29/9.33/9.33s. Remaining cases were stopped after rejection; `inline-screen.json` is a partial screen, not a passing complete suite.

The templates in the first direct version retained out-of-line notification calls. Forcing their inlining also failed to produce a speedup. The results reject these implementations; they do not prove every possible static propagation design is ineffective.

`withdrawn-inline.patch` reproduces the final candidate against M127 `e49b00ae`; copy the accompanying `controls.sv` to `tests/static_notify/controls.sv` first. The shared test harness exercised eight original models: 80 waveform captures, 2104 budget comparisons, 16 prediction comparisons and 576 resume comparisons, including 107 existing reference failures. A newly added control fixture initially had an incorrect startup-count oracle; corrected separate execution passes 10 captures, 263 budgets, two predictions and 72 resume comparisons, including ten existing reference failures. Do not call all resume comparisons successful continuations. Two sanitizer programs passed. These correctness results are independent of the runtime rejection.

Raw generated DSIM models, native executables and complete measurement logs are kept privately on 103 under `/tmp/dsim-m128-static-{notify,direct,inline}`. Vendor binaries/code are outside these directories and are not included in source artifacts.

The 378-member timing archive is verified on readback and mirrored at both stable prefixes; `raw.json` and `mirrors.json` identify it. The implementation that supersedes these failed candidates is documented in [M129](../m129-compiled-activation/README.md).
