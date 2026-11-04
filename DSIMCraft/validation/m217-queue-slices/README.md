# M217 — UVM queue slices and function output

Five unchanged fixtures match VCS W-2024.09 source hashes and TRACE output.
Default/shared/shared+time-wheel native programs pass 15 complete captures;
five specific negative diagnostics preserve existing output. Both the frontend
and five generated programs pass ASan/UBSan, with identical generated C++ and
full shared waveforms. Previous 21 models retain identical C++ in all 63
normal/shared/wheel combinations; this reuses M216 native evidence and is not
claimed as 63 new native runs.

The first negative-test expectations were corrected to match the actual parser
stage; original failing logs remain in the persistent evidence directory.
VCS rejected the exploratory direct-slice method/constant-function and event
probes. The committed positive fixtures use materialized methods and portable
bounds; rejected probes are not counted as positive VCS evidence.

The unchanged complete UVM library advances beyond the queue-slice and recorder
function-output blockers to an elaboration binding exception, `map::at`.
Normal and sanitized frontends reach the same blocker; no full generated model
or successful run_test is claimed. Left-side slices and nested selections are
still limited. See docs/queue-slices.md.

Persistent raw work: `dsim-test/evidence/m217-array-args-debug` (including SDK
27.0 removal/cache failures, restored SDK 27.2 builds, early diagnostic attempts,
positive native programs, complete waves and sanitizer logs). No runtime speed
comparison is included.

Production source `cb4c06c9` is pushed to GitHub. Mac stable
`20261102T075107555780Z-766daf8247bd` is active; mandatory parser/format/native DB
checks and the new 15-capture/five-rejection group pass from the clean frozen
revision. Five actual-entry emissions match the candidate's native inputs and
the corresponding validated native programs run successfully after activation.
See `mac-release.json` (native artifacts are reused after byte identity).
The returned-queue model also passes an actual failed prediction and rollback;
its complete ordered capture matches the normal shared execution
(`rollback.json`). This is an additional native run after publication.

103 Intel stable `20261102T080524576549Z-766daf8247bd` is active. The frozen
M217 source passed its 15-capture/five-rejection group and mandatory parser,
format and native DB checks. All five actual-entry emissions match the
validated native inputs; the corresponding native programs were reused and
rerun successfully. See `linux-deployment.json`.
