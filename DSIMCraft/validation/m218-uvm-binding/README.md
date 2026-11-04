# M218 — UVM late binding and string queries

The unchanged complete Accellera UVM 2020.3.1 library reproduces M217's `map::at`
failure. A method binding creates a new concrete class specialization after the
initial scan. Registering it at the declaration's lexical scope fixes that miss.
The initial fix exposed an unbound static initializer; ASan/UBSan found a null
semantic scope in `veri_declared_type`. Completing deferred semantics before
lowering the new class removes this failure. Original failed logs are preserved.
New base/nested classes also receive initialization, with duplicate protection.

Five identical source fixtures match VCS W-2024.09 TRACE output and hashes;
the formatted specialization also matches exact file bytes `ab/8\ncd/9\n`.
Default/shared/shared+time-wheel pass 15 native captures and two negative
output-preservation checks. Both the frontend and five generated native programs
pass ASan/UBSan; their C++ and complete decoded shared waveforms match normal
builds. These small fixtures check semantic contracts; they do not reproduce the
full library's original late-registration exception. The string-query fixture
also fails on M217 with its original erroneous integral-unary diagnostic.

The previous 26 models retain identical C++ in all 78 normal/shared/wheel
combinations. Earlier native results are reused; these are not 78 fresh native
runs. Additional class regression details are in `class-regressions.json`.

The full unchanged library now reaches the same explicit unsupported `$swrite`
without a format string in default, shared and sanitized builds. No generated
full model or successful `run_test` is claimed. Sanitized frontend checks use a
64 MiB host stack and `ASAN_OPTIONS=detect_leaks=0:symbolize=0`; the earlier null
scope sanitizer failure is retained separately. An initial reproduction wrapper
incorrectly assumed the exported library had `.git`; it was corrected to use the
existing upstream provenance record and fixed package SHA.

Persistent raw evidence is in `dsim-test/evidence/m218-uvm-binding`, including
initial failures, full-library traces, native programs, waveforms and build logs.
This batch contains no runtime speed comparison and no new C910 result.

Production `50e6e8d2` is pushed to GitHub. Mac stable
`20261102T110323483154Z-f6931fb0e2e5` is active from a clean frozen revision.
The focused 15-capture/two-rejection group and mandatory parser, format and
native DB checks pass. Five actual-entry emissions match their validated C++;
those native artifacts are reused and rerun with identical complete waveforms.
See `mac-release.json`.

103 Intel stable `20261102T110340708187Z-f6931fb0e2e5` is active. The frozen
M218 build passed its 15-capture/two-rejection group and mandatory parser,
format and native DB checks. Five actual-entry emissions matched validated
C++ and the corresponding native programs were reused and rerun successfully.
See `linux-deployment.json`.
