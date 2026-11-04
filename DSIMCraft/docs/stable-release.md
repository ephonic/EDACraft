# Local stable release

The requested stable entry is `~/vibe-coding/dsim-test/bin/dsim`. After a functional
batch passes its targeted regressions and compatibility checks, update it with:

```sh
python3 scripts/publish_stable.py
```

For an incremental functional batch, `--check-group` selects the affected groups
explicitly. Parser and format-parser checks, immutable runtime snapshots, source
hash checks and atomic activation still apply. The release manifest records the
selected scope; this mode does not claim a full regression run. For example:

```sh
python3 scripts/publish_stable.py --check-group string_subroutines --check-group strings
```

Without this option, the existing full release checks run, including the new
string subroutine regression. Legacy regression scripts receive a copy of the
build cache beside the candidate binary.

The publisher builds Release mode in `build-stable`, snapshots the runtime
headers into a new release directory, and embeds that immutable runtime path in
the compiler. It checks compiler input hashes before and after building, compiles
and runs static/automatic/wide RTL and a real two-partition model with DWF output,
and runs the gate-source CLI regression including SDF binding. Fixed array
initializers and all six reported-case fixtures are checked too; a compilation
budget or output mismatch prevents publication. The twelve frontend compatibility
models additionally check packed dimensions, generate updates, automatic roots,
and both keyword modes before publication. Seven module/primitive instance-array
models cover port slicing/broadcast, independent state, electrical links, wide
values, delays, generate scopes and two actual partitions. Only after those
checks pass does it atomically replace `bin/dsim` with a symlink to that release.
Earlier releases are retained. A failed build or smoke test preserves the current
entry. `--prefix` and `--build` support other local locations.

Each `releases/<timestamp>-<source hash>/release.json` records input hashes, Git
commit/dirty state, binary hash and smoke results; build and run logs are next to
it. This is a local macOS installation and requires the existing C++ compiler and
libzstd. Future accepted stable batches should run the same publisher again;
there is no background updater publishing untested worktree changes.

The M92 publisher also runs `tests/unpacked_state/regression.py` with the explicit
build configuration before activation: 52 captures, four failed prediction
replays and a packed-storage control. Its six fixture/script files are included
in the hashed release inputs.

M102 (`511594b`) was published to both stable entries on 2026-10-25. Each host passed eight targeted checks: RTL/parser cleanup, format parsers, native Liberty DB, testbench I/O, strings, final/bind, archived cases and gate-source/SDF flow. The 629 macOS input hashes and all 1590 packaged source files were checked against Git; eight runtime snapshots per host and both activated entry points were verified. Installed compilers regenerated 14 programs per host and compiled/ran the automatic/ref/plusargs/final fixture. Cross-platform comparison matched 100 C++ sources, 129 VCDs and 179 runtime outputs. See [M102 evidence](../validation/m102-testbench-io/README.md); these are targeted checks, not a full regression or new performance measurement.
