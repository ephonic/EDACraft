# M73: RTL module and primitive instance arrays

Implementation uses the existing instance-name/range AST, independent compiler
scopes, port adapters and net bit links. No grammar, compact gate parser,
scheduler or checkpoint layout changes are made. See
[the feature boundary](../../docs/instance-arrays.md).

Seven shared models cover ascending/descending/negative/parameter bounds,
packed split and broadcast ports, named connections, independent delayed NBA
state, inout resolution and reverse input-net drive, 210-bit concatenated
variable/two-state outputs, twelve logic/tristate primitive kinds and rise/fall
delays, parameter/generate clones and per-instance static function locals.
The array of two independent workers executes in two actual partitions.

- Native regression passes 87 captures (three backends, ordered/settled,
  VCD/DWF plus three failed-prediction replays), 11 rejection diagnostics and
  actual two-partition output checks. Final CTest: 82.91 seconds under load.
- Real VCS W-2024.09_Full64 on `10.131.254.103`, after
  `source /apps/EDAs/syn.bash`, passes all seven same-source TRACE models.
  All **2858 exported physical bit settled timelines** agree, with no excluded
  bits. VCS combines six generate/instance scope names (for example
  `g[0].s[1]`); the comparator records the explicit split into nested scopes.
  Six read-only 32-bit wires export automatic-function static locals because
  this VCS build omitted them from both whole-root and explicit-variable dumps.
  All 192 such bits are compared to the actual dsim locals, not removed.
  `probes/` retains the unsuccessful direct-dump attempts.
- Seven actual sanitized compiler generations and executed generated programs
  pass ASan/UBSan, complete generated C++ identity and ordered stream/stdout
  comparison, including actual parallel execution. Repeated parser semantic
  analysis/clone/cleanup also passes the instrumented executable. Leak detection
  is disabled; this is a local macOS check, not Linux or a full-suite claim.
- Ten distinct relevant checks pass: the new regression, legacy primitive-group
  regression, and eight affected CTests listed in `results.json`.
  Legacy primitive groups additionally pass 432 waveform captures, 1152 truth
  observations, 48 named/unnamed/mixed complete C++ identities and 24 complete
  named C++ identities against the previously published M72 compiler.
- `dsim-test/cases` still has the same six top-level reports and carry followup;
  inventories are recorded and all six fixtures remain mandatory release tests.

The first new regression completed its positive/replay models but expected the
wrong spelling for the existing variable-driver conflict diagnostic. The final
full rerun passes with the correct diagnostic. The first legacy primitive test
failed on pre-existing protected waveform outputs; the runner now removes only
its own outputs before capture, and its complete 24-group/72-program rerun
passes. Its former array rejection used a now-legal scalar broadcast and was
replaced with an actual mismatched-width case. The initial sanitizer build named
a non-existent extra target after successfully building dsim; the correct parser
target was built and its instrumented executable was run directly (CTest is not
registered in that build). These intermediate failures are retained in logs.

Reproduce native coverage with:

```sh
ctest --test-dir build -R '^rtl_instance_arrays$' --output-on-failure
python3 validation/m73-instance-arrays/verify.py
python3 validation/m73-instance-arrays/run-sanitizers.py /tmp/dsim-m73-sanitizers
```

`run-vcs.py` accepts the fixture directory and an output directory on the VCS
host. Sources, commands, vendor compiler/run logs and waveforms are in `vcs/`.
`native-results.json`, `primitive-compatibility.json`, `sanitizers/results.json`
and `vcs-bit-results.json` record the independent checks. No new speed benchmark
or complete VCS/SystemVerilog feature parity is claimed. Unpacked ports inside
instance arrays, multidimensional instance arrays, dynamic output/inout selects
and persistent side effects in terminal expressions remain explicit boundaries.
Stable publication is recorded below.

## Stable publication

Implementation `cf3d426b837392cde5f3c03230deb854a71d59cb` was published to
`~/vibe-coding/dsim-test/bin/dsim` after all **32** release checks passed,
including all six reported-case fixtures and gate CLI/SDF checks. The immutable
release snapshots all eight runtime headers. Binary SHA256:
`bac7f953e1db8ab0a316398c69609a186fb45cb8e7d522dba430e7589014e0da`.
`stable-release.json` records complete input hashes; `stable-publish.json` is the
publisher summary, and `stable-reported-cases.json` records the six-case results.
The dirty flag reflects the preserved untracked user `experiments/matvec16/`,
which was not included in the implementation commit or compiler inputs.

`stable-identity.json` verifies all 30 complete generated C++ files, stdout and
matching-mode waveform streams: seven new programs against accepted native M73,
and 23 existing programs against the previous M72 release. Two Verilog keyword
models use their default settled mode; all others use ordered mode. Reproduce
with `python3 validation/m73-instance-arrays/verify-stable.py PREVIOUS_RELEASE`.
