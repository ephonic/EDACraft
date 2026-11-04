# Automatic scalar function storage and single-core efficiency

M110 keeps eligible automatic function parameters, return values and local variables in host-local four-state `V` values during a call. This removes repeated generic signal loads/stores and their notification checks. Each local has a scope guard that writes its final value back on normal return and exception unwinding, including an execution-budget failure. Instruction steps and the original PC control flow are retained. Two-state destinations still discard unknown bits on every assignment.

The compiler accepts only input-only, nonrecursive, automatic scalar storage of at most 64 bits, with at most 16 local slots. The lowered body must use only get/set/step runtime operations. It rejects quoted fragments, nonlocal writes, ref/output arguments, dynamic storage, arrays, nested calls and bodies using the existing native integral-loop path. These use their previous implementation. Static function state also retains its previous implementation.

At runtime, caching requires no aliases, signal watches, force or mixed-state mask on any cached slot. Waveform-enabled code, properties, timing checks/paths and dynamic fork frames disable this path. A parallel resolved-value observer also disables it. The optimization therefore targets ordinary single-core, no-wave execution. This does not expand the supported language subset or introduce additional worker threads. `DSIM_RTL_REFERENCE_FUNCTION_LOCALS=1` selects the original stores for differential testing.

On the original unchanged REPORT-PERF workloads, GCC 11.5 `-O2 -pthread`, CPU 0, one warmup and three rotated rounds against frozen M109 and VCS W-2024.09_Full64:

| Workload | M109 CPU / wall (s) | M110 CPU / wall (s) | VCS CPU / wall (s) |
| --- | ---: | ---: | ---: |
| CPU | 16.81 / 17.23 | 17.13 / 17.35 | 5.84 / 9.75 |
| CRC | 6.30 / 6.32 | 5.24 / 5.26 | 3.89 / 7.70 |
| muldiv | 11.87 / 11.92 | 11.97 / 12.13 | 7.04 / 10.69 |
| AXI4 | 0.26 / 0.27 | 0.25 / 0.26 | 0.57 / 3.39 |

CRC CPU time decreases 16.8%, to 1.35 times VCS. CPU's two executables are byte-identical; their 1.9% timing difference is measurement variation, not a generated-code change. Muldiv does not show a stable runtime improvement. AXI4 is too short for a throughput claim. The shared host is not frequency-locked, all samples are retained, and VCS wall time includes its startup overhead. All 48 outputs and raw time logs were audited. CPU/CRC/muldiv remain 2.93/1.35/1.70 times VCS CPU time in this round; one-core affinity does not establish a one-software-thread process.

The same 200000000-tick active prefix retains exactly the same executed-step counts and full signal-state hashes in all three designs. Callgrind instruction counts decrease from 98615106 to 87393743 for CRC (11.4%) and 96579814 to 95858721 for muldiv (0.75%); CPU remains 461207692. Instruction reductions are not CPU-time measurements. Simple set/notification splitting and forced hot-path inlining were screened and withdrawn after regressions; they are not in the release.

The new regression checks four-state arithmetic, signed 64-bit shifts, two-state conversion, static persistence and nonlocal effects, with 12 complete ordered/settled VCD captures, 187 exact budget/state comparisons and two prediction accept/reject runs across serial, time-wheel and thread-requested fallback. Instrumentation confirms 72 cached calls without wave support and zero with it. Existing subroutine, event-expression, integral-type/loop, wait-rearm, runtime-window, REPORT5/6 and testbench-I/O regressions pass. Actual generated code passes ASan and UBSan. Detailed measurements and release receipts are in [M110 evidence](../validation/m110-single-core/README.md).
