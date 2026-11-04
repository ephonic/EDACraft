# M92 — unpacked struct storage state

Implementation: `1a7cb0d3462fd5605598019f0ad30f8207d959af`.
Scope and remaining boundaries: [unpacked-state.md](../../docs/unpacked-state.md).

Unpacked `bit` members previously converted on read, but selected/concatenated/
compound and event-NBA writes could retain unknown physical bits. A comparison
of the complete struct then differed from VCS. Declaration defaults also used
pre-collapse IDs after deterministic signal ordering, and subroutine struct
storage lacked aggregate defaults. The compiler/runtime now use declaration
masks at commit, remap defaults/masks, and initialize subroutine aggregate slots.
Mixed packed members retain shared raw X/Z; ordinary packed designs do not enable
the mixed-state feature, metadata or commit branch.

## Verification

- `baseline.json`: the previous installed M91 compiler compiles all four new
  fixtures. Three terminate at value assertions; the partitionable fixture sets
  both error bits to one. A zero process exit alone is not considered correct.
- `native-check.json`: four models, 52 ordered/settled VCD/DWF captures across
  serial/time-wheel/threads; four failed prediction replays, two actual partitions,
  explicit SystemVerilog value oracles and a separate mixed-packed control.
- `vcs-check.json`: byte-identical inputs, exact TRACE output and all 728 common
  physical bits' settled timelines equal to VCS W-2024.09_Full64. There are 468
  explicit member-declaration mappings, no VCS-only bits, and 64 native-only array
  bits not dumped by VCS. Those 64 bits are not claimed as compared.
- `related-tests.json`: existing packed aggregates, complex REPORT, assignment
  patterns and interfaces CTest groups pass.
- `sanitizer-check.json`: 16 actual ASan/UBSan program executions (all four models
  × serial/wheel/parallel/replay), exact ordered timelines, and 12 complete C++
  identities from the sanitized compiler. Leak detection disabled.
- `startup-rollback-check.json`: two additional ASan/UBSan executions roll back
  from before any process runs, covering complete startup writes and automatic
  struct activations. The four ordinary replays additionally cover pending NBA
  and parallel updates; the zero-time fixture replays start after time-zero work.
- `native-artifacts.json`: 133 full-content identities, including 16 generated
  C++ programs, 65 execution outputs and 52 waveform captures. Platform and
  release comparisons use every listed identity, not sampled prefixes. Linux has
  seven ordered wave byte differences: independent `calls`/`index` changes at
  time zero swap relative order, while every per-signal timeline is identical.
  `linux-wave-order.json` retains the actual VCD diff. Cross-channel ordered byte
  identity across platforms is not claimed.
- `source-package.json`: all 1466 archive files match the implementation commit.

## Published stable entries

macOS: `~/vibe-coding/dsim-test/bin/dsim`, release `20261025T072138064213Z-4c3887e12a86`,
binary SHA256 `a83e4dffc07a3eca9b1b8c2f7838c537cbd16df7bbaf2ec7f8c996ea0d84fbb1`. All 74 publisher checks
pass; all 507 input hashes match the implementation commit,
with eight immutable runtime headers. `installed-local-check.json` recompiles four
models from the actual entry and checks complete C++ and whole VCD byte identity.

Linux: `/apps/EDAs/own/dsim/bin/dsim` and `/apps/EDAs/own/dsim/dsim`, release
`20261025T072212Z-1a7cb0d`, binary SHA256 `66f9934c664279972d898e5f912b0ae92cd5481c34bcb492466777409f4d5be7`. All
11 groups pass; all 1466 source files and
eight runtime headers are verified. Actual installed-entry recompilation under
the VCS environment matches the Linux reference C++ and whole VCD bytes for all
four models. The cross-platform ordered interleaving difference remains recorded
separately; per-signal timelines, outputs and full generated C++ match.


## Reproduce

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --target dsim -j 4
python3 tests/unpacked_state/regression.py build/dsim /tmp/unpacked-state
```

On the VCS host, put the four fixture files under `/tmp/dsim-m92-vcs-inputs`,
source `/apps/EDAs/syn.bash` and run `run-vcs.py`. Compare copied results with:

```sh
python3 validation/m92-unpacked-state/verify-vcs.py \
  --native /tmp/unpacked-state --vcs /tmp/dsim-m92-vcs --output /tmp/vcs-check.json
```

`run-sanitizer.py`, `check-installed.py`, `export-artifacts.py` and
`compare-artifacts.py` reproduce their respective checks. The Linux publisher
records an immutable runtime snapshot and only switches both stable aliases after
all selected checks pass.

Raw generated programs, waves and logs stay outside Git. `archives-check.json`
lists permanent evidence archives under `~/vibe-coding/dsim-test/evidence/m92-unpacked-state/`;
the VCS archive is also at `/apps/EDAs/own/dsim/evidence/m92-unpacked-state/`.

## Additional REPORT3 review

The original p27 source is retained under `probes/`. `report3-check.json` shows
all six output lines and all 422 physical bits equal to VCS, with no omitted bits.
The probe itself labels three legal context-dependent results as “BUG”; VCS
prints the same labels/results. The report’s P0 classification is not evidence
of a dsim discrepancy. Signed/unsigned ternary context affects `>>>`, `/` and `%`;
no compiler semantics were changed for this report. `verify-report3.py` and the
separate raw evidence archive reproduce this check.
