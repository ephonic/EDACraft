# M86 complex RTL report repair evidence

The input is preserved as [input-REPORT.md](input-REPORT.md); its unchanged source
fixtures are under `tests/complex_report/`. Implementation scope and boundaries
are in [complex-report-fixes.md](../../docs/complex-report-fixes.md).

Accepted original-source results: 17 probes and six complex designs pass. Eight
additional models produce 27 matching complete ordered captures across serial,
time-wheel, threads and three failed prediction replays. Sixteen invalid or
unsupported sources receive explicit diagnostics; the budget exhaustion test
also passes. The six legacy fifo/alu/uart/fir/cdc/svfeatures designs pass.

Actual VCS W-2024.09: all 25 same-source self-check outputs match. Three original
probes need `-ignore initializer_driver_checks`; both default rejections and
compatible logs are retained. Six boundary models expose 261 common physical
bits with identical full settled timelines. The 1616 native-only array/storage
bits are listed individually. Two tests finish at time zero before the VCS dump
wrapper starts, so they have self-check comparison only, not waveform coverage.
No missing or mismatching signal is silently excluded.

Known VCS differences are retained: dynamic integer out-of-range selection is
0 in VCS versus X in dsim; VCS's identical duplicate declarations produce IPDW
warnings while dsim follows the report's requested semantic-error policy. These
cases are not included in passing equivalence claims.

Final sanitizer checks cover eleven actual generated programs (including three
rollbacks), the parser's repeated clone/cleanup checks, sixteen compiler
rejections, and native/ASan recursion-depth-limit failures. Full generated C++
for the eight positive models is identical to native acceptance before compiling
and running with ASan/UBSan. Existing four subroutine/two-state/function-event
CTest groups pass after updating obsolete negative expectations for newly valid
constant functions and direct automatic recursion.

The first publication stopped on a real regression in strings/automatic: the
integral constant evaluator queried a runtime string local's width. It was fixed
by rejecting nonintegral candidates before evaluation. Initial publication logs
are preserved under `publication-initial/`; the stable entry was not switched.
The first Linux deployment was stopped before activation. Final source commit
is `2002762c67a95a3614330cd1bb001d3c25e0beb9` (build implementation plus regression
expectations); release results are recorded separately after completion.

Recheck retained acceptance with `python3 validation/m86-complex-report/verify.py`.
The stable and Linux verification scripts also check complete output/waveform
identity rather than only final values. No DWF encoding or performance claims
are included.

Final releases both passed and were activated. macOS has 65 passing publication
groups, then six legacy designs tested through the installed entry; all 27 new
generated programs match native acceptance byte-for-byte in C++, output and
complete ordered waveforms. Immutable source/runtime/binary hashes pass.
[stable-release.json](stable-release.json) records the exact release and hashes.
Linux parser/complex/sampled/concurrent/gate checks pass; the additional complete
strings regression passes 31 captures / 4 rollbacks / 30 rejections. Its 17 probe,
six design and 27 capture outputs/waveforms equal macOS. After sourcing syn.bash,
the installed entry compiled and ran functions, force and strings again.
[Linux release metadata](linux/release.json) and installation logs are retained.
The two final verification scripts can be rerun from this repository.
