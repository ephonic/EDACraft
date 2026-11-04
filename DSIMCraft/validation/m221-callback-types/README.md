# M221 — callback specialization type compatibility

The unchanged complete public UVM library is the actual regression reproducer.
The diagnostic build identifies both source `uvm_callbacks#(uvm_event#(string),
uvm_callback)` and destination `uvm_typed_callbacks#(uvm_event#(string))` as semantic
types without registered runtime layouts. Compatibility had searched only the
layout table. A separate semantic identity cache now follows the source type's
base-class chain without allocating a layout or running static initialization.

Five same-byte fixtures match VCS W-2024.09 traces and source hashes. They verify
callback singletons, inherited self typedefs, local type contexts, transitive
upcasts, parameter isolation, input/output conversion, strict reference binding
and virtual dispatch. The small fixtures also compile with M220; they validate
contracts rather than independently reproduce the full library's late-type miss.
Six unchanged invalid sources are rejected by both VCS and dsim: downcasts,
unrelated types, parameter mismatches and non-identical ref/const-ref types.

All 15 positive native captures passed before the initial regression wrapper
stopped on an overly broad expected `ref` diagnostic. The expectation was
corrected to the actual class-specific diagnostic; all six negatives were then
rerun with output protection. The initial failed wrapper and its positive native
artifacts remain external. Final release validation reruns the complete group
with the corrected expectations; only that full release result is called PASS.

The unchanged full library advances to `uvm_reg_item.svh:281`: a class member
dynamic array used as a `ref` actual still requires a heap-backed array alias.
Default/shared/sanitized frontends agree on this next blocker. No full generated
UVM model, native program or successful `run_test` is claimed.

The prior 59 models retain identical full C++ in all 177 default/shared/wheel
combinations. Existing M220 native evidence is reused; these are not 177 new
native runs. No new runtime performance ratio or C910 result is included.

Persistent raw evidence: `dsim-test/evidence/m221-callback-types`, including the
original/diagnostic full-library failures, unsuccessful small-probe reductions,
all generated programs, waveforms and initial wrapper failure.

The sanitized frontend and all five generated native programs pass ASan/UBSan;
their C++ and complete ordered captures match normal shared builds. A forced
failed prediction restores callback singleton aliases and full waveforms.

Production `d4e47c36` is pushed to GitHub. Mac stable
`20261102T132227242813Z-3e6674b1dd76` is active from a clean frozen revision.
The complete corrected group passes all 15 captures and six compile rejections,
plus mandatory parser, format and native DB checks. Runtime header bytes match
M220. Five actual-entry emissions match validated native inputs; those native
programs are reused and rerun with full waveform identity. See `release-group.json`
and `mac-release.json`.

103 Intel stable `20261102T132430067258Z-3e6674b1dd76` is active. Its frozen
M221 build passed all 15 captures, six compile rejections and mandatory parser,
format and native DB checks. Both root/bin entries resolve to the new release
and pass `--help`; five actual-entry emissions match validated native inputs and
those native programs were reused and rerun successfully. Their source SHA,
five complete generated C++ files and full TRACE outputs match the Mac release.
See `linux-release.json` and `linux-deployment.json`.
