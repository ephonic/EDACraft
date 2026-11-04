# M107 batch diagnosis

The original RTL measurements do not enable `DSIM_BATCH_ENABLED`. Existing `--gate-batch` consumes only the FIFO-ready prefix of the same compiled gate handler/context. It preserves every per-cell drive, sensitivity rearm, event budget step and observable update. It reduces dispatch/context overhead; it neither fuses RTL processes nor removes intermediate values. `include/dsim/runtime.hpp::compiled_batch`, `docs/gate-batches.md` and `src/rtl_compiler.cpp`'s runtime macro selection establish this scope.

`census.py` instruments the actual M107 generated C++, runs a fixed 200000000-tick prefix, and requires exact step counts and complete signal-state hashes from the independently checked baseline prefixes. These counters are diagnostics, not timings or full-workload totals:

| Prefix | Process dispatches | set calls | Actual set changes | drive calls | wait rearms | Watch visits | Native-loop guard accepts/attempts |
|---|---:|---:|---:|---:|---:|---:|---:|
| CPU |1261646|1398727|921690|873632|1201657|2008686|0/0|
| CRC |144694|673443|596593|64688|104692|344694|15062/15062|
| muldiv |221901|336741|271947|121894|181900|537310|0/0|

The CRC prefix already executes eligible native loops; their guard does not fail here. CPU/muldiv do not enter that path in these prefixes. These facts distinguish missing eligible computation fusion from an existing fast loop being repeatedly rejected.

The M106 callgrind prefixes independently locate substantial instruction cost in `Sim::set`, `drive`, wait rearm and the scheduler. The adopted M107 single-driver path reduces full-workload CPU time by 6.1% / 5.2% / 9.4% on CPU/CRC/muldiv while retaining their outputs. This is evidence that per-signal overhead matters, not a measurement of batch fusion's potential benefit or of VCS's internal execution counts.

The structural next optimization is larger compiled RTL evaluation regions, with intermediate values held locally when they cannot be observed. Candidate regions need explicit event/sensitivity, NBA, force, alias/multiple-driver, four-state, timing, waveform and rollback boundaries. Legal execution order must be preserved; collapsing all deltas to a final settled value is not a general replacement. First compare a guarded fused candidate with the existing path on full unchanged workloads and complete event/state checks. Do not enable fusion based on inferred benefit alone.

The remote `/home/yangfan/vcs/vcs1017.md` was re-read for this diagnosis. Its RTL sections describe word-level compiled expressions and evaluation blocks; its symbol observations do not establish that any particular dsim fusion strategy matches VCS internals. No speedup estimate is derived from that document.
