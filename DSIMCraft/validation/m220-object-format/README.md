# M220 — class formatting

Six final same-byte fixtures match VCS W-2024.09 TRACE output and source hashes.
They cover null/dynamic/inherited layouts, static updates, protected/shadowed
properties, parameterized references, cycles, scalar/enum/real/string fields,
queues/dynamic arrays/maps, static containers, events, function ordering and
explicit event controls. A seventh native-only fixture checks dynamic formats
and literal percent data; it is not claimed as VCS alignment. Default/shared/
shared+time-wheel pass 21 complete ordered captures, with identical decoded
waveforms, two output-preserving compile diagnostics and three runtime rejects.

Initial probes are preserved externally. VCS consumed `%0d` inside class string
fields and emitted non-UTF8 bytes for dynamic `%p`; the first oracle wrapper
stopped decoding those bytes. They were not normalized into positive results.
Final oracle fixtures use ordinary strings and constant class formats. dsim's
separate native-only tests retain literal percent data and support dynamic class
formats. A probe also showed different implicit-class sensitivity behavior;
this path is explicitly diagnosed rather than silently claimed as aligned.

The first implementation rendered object contents after evaluating all arguments.
The VCS side-effect probe instead snapshots the class before a later argument
mutates it. Rendering now happens once at each object's evaluation point.
Unsigned member rendering, empty-container spacing and map-key radix were also
corrected against the oracle. All initial programs and results remain outside Git.

Class descriptions are immutable owned metadata and have stable emission order.
They are installed before initializers and read the current heap and static
signals. Fixed-array/struct/chandle members and numeric class conversions have
explicit runtime diagnostics; non-class `%p` and implicit class formatting remain
unsupported. See `docs/object-format.md` for the scope and boundaries.

The unchanged complete public UVM library now reaches a callback-specialization
handle assignment at `uvm_callback.svh:607`. Default/shared/sanitized frontends
agree. No complete generated UVM model, native program or successful `run_test`
is claimed. No new performance comparison or C910 result is included.

Persistent raw evidence: `dsim-test/evidence/m220-object-format`, including all
initial VCS bytes, failed expectations, native programs, complete waves and logs.

Both the frontend and seven generated native programs pass ASan/UBSan. Their
complete C++ and ordered captures match the normal shared build. Emitting in
stable class-ID order leaves all seven normal inputs byte-identical. Two actual
failed predictions (function mutations and containers) restore output and full
waves. The five scalar-write models are rebuilt in all three modes (15 captures,
four compile and three runtime diagnostics). The seven previous text-I/O models
also pass all 49 captures and seven rollbacks; native artifacts are rebuilt.

Production `3267ccee` is pushed to GitHub. Mac stable
`20261102T124301359346Z-7f6816810905` is active from a clean frozen revision.
Both focused groups pass 36 captures, six compile and six runtime diagnostics,
plus mandatory parser, format and native DB checks. All seven actual-entry
emissions match validated native inputs; those native artifacts are reused and
rerun with complete waveform identity. The new lowering include is part of the
frozen input manifest. See `mac-release.json`.

103 Intel stable `20261102T124320383082Z-7f6816810905` is active. The frozen
M220 build passed both selected groups and mandatory parser, format and native
DB checks. Seven actual-entry emissions matched validated C++; their native
programs were reused and rerun successfully. See `linux-deployment.json`.
