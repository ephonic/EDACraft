# M219 — display-style string writes

Five unchanged final fixtures match VCS W-2024.09 source hashes and complete
TRACE output. They cover unformatted signed/unsigned/wide/four-state/real/null
scalars, empty output, multiple/dynamic format segments, literal conversion,
time/scope output, radix defaults, function side effects, class string fields,
string queue elements and packed destinations. Default/shared/shared+time-wheel
pass 15 native captures with identical complete decoded waveforms. Four compile
rejections preserve an existing output; three invalid runtime formats reject.
A forced failed prediction restores function side effects and string values,
with identical output and complete waveform after rollback.

Class/chandle and unpacked aggregate output remain explicitly unsupported.
The unchanged complete UVM package still stops at `uvm_pool.svh:249` when
`$swrite` receives a class value. Default, shared and sanitized frontends agree;
no full generated UVM model or successful `run_test` is claimed. VCS prints class
contents rather than an integer handle, as recorded by the exploratory probe.
This batch completes scalar/format semantics, not this remaining object printer.

The old text-I/O regression contained a stale negative case expecting dynamic
`%f` to be unsupported. Actual M218 compilation/running of that unchanged case
already succeeds. The negative uses invalid `%q` instead; all seven old models,
49 captures, seven rollbacks and remaining negative checks are rerun unchanged.
The late-class group is also rebuilt and rerun, not reused across runtime-header
changes.

Initial exploratory failures remain external: `small` was a reserved keyword
in the first VCS probe; the initial positive target used a fixed string array,
which dsim still rejects. The final fixture uses an already supported string
queue. VCS's destination index `index++` probe increments twice; it is kept
separately and not imitated or counted as a corrected portable case. A sanitizer
wrapper initially compared a waveform before its independent producer finished;
the failed logs are retained and final checks run after normal captures exist.

Persistent raw evidence: `dsim-test/evidence/m219-swrite`, including all failures,
original probes, full-library diagnostics, generated native programs and waves.
No new runtime performance comparison or C910 result is included.

Production `bdb16dcd` is pushed to GitHub. Mac stable
`20261102T115032409299Z-d06d3613cbe9` is active from a clean frozen revision.
Both string-write and late-class groups pass on the final runtime snapshot
(30 captures, six compile rejections and three runtime rejections), together
with mandatory parser, format and native DB checks. Five actual-entry emissions
match their validated native inputs; those native programs are reused and rerun
with complete waveform identity. See `mac-release.json`.

103 Intel stable `20261102T115058493783Z-d06d3613cbe9` is active. Its frozen
M219 build passed both selected groups and mandatory parser, format and native
DB checks. Five actual-entry emissions matched validated C++; the corresponding
native programs were reused and rerun successfully. See `linux-deployment.json`.
