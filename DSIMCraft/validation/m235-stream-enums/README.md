# M235 — typed runtime streams and large UVM packing

Preserve the declared enum identity on the runtime-sized branch of an explicit packed bit-stream cast, just as the existing fixed-sized branch does. Implicit integral/stream assignment to an enum still fails in dsim. The VCS oracle accepts the retained implicit streaming-assignment boundary; that stricter dsim behavior remains a visible difference, not an alignment pass. Signed values, class fields and typed function returns are exercised by three same-byte VCS models, nine native complete ordered captures and one protected compile boundary.

The original full Accellera UVM 2020.3.1 packing test now runs `uvm_field_int` on an 8192-bit four-state field. It packs a nontrivial value with bits across the vector, clears the original, unpacks into an independent object, and compares every bit. It reports `TRACE REAL_UVM_SMOKE PACKING 8196 8196`, with zero UVM_ERROR/UVM_FATAL. Library tree SHA and test source SHA and all TRACE match VCS. Native verification uses UVM_NO_DPI and -O0; no UVM sources are patched.

M234 real-DUT virtual-interface integration and M233 field utilities remain validated. The M234 complete-library frontend/native ASan/UBSan pass; the three enum frontend/native sanitizer models and the lexical-shadowing sanitizer pass. The complete packing frontend/native ASan/UBSan execution also passes with complete generated C++ identical to the normal input. First property fixture had no dumpable scalar signals; adding an observable enum retains class-field coverage and enables complete wave comparisons. Its original failed attempt is retained.

Fix the virtual-interface regression's optional case filter to accept the publisher's CMakeCache argument. A publisher-shaped invocation with cache + selected cases passes. The earlier immutable M234 candidate is rejected without replacing the previous stable entry; the corrected combined production source is staged afresh. No frozen source is edited to rescue that candidate.

Remaining major gaps include joint object-graph randomization, DPI open arrays, sample-argument coverage, full SVA/VPI and the documented virtual-interface subset boundaries. No general UVM/VCS compatibility percentage or performance claim is made. Raw evidence: `dsim-test/evidence/m235-stream-enums/` and `m234-virtual-interfaces/`. Both local and 103 stable entries are activated and verified; receipts are recorded below.


Production `a0cc8b571775ce42279f0dba7a8b66166f39bb0a` is pushed. Mac
`20261104T060449560625Z-8991211ac28a` and 103 Intel
`20261104T060449622672Z-8991211ac28a` are active, with identical complete source SHA
`8991211ac28a0f2823ff3ccfaada039d66bd3c217bb3a24e9633ac63bd62d666`.
Each immutable release passes four groups: 127 captures, 33 compile boundaries,
five runtime rejections, four existing interface failed predictions and the real
two-partition interface check, plus mandatory parser/format/native DB checks.
The dsim/VCS rejection differences above remain classified separately.

All 96 complete generated C++ inputs and 96 decoded ordered waves for the three
new groups match across hosts. All 32 actual-entry model emissions match their
validated native input before reuse, rerun successfully, and match complete waves
across hosts. Both 103 aliases resolve to the same verified binary. Three new
enum and one lexical sanitizer models match frozen C++ and full waves; fourteen
previous stream/interface sanitizer inputs also match the final frozen models.
The original UVM real-DUT and wide-packing frontend/native sanitizer programs pass.

Both actual stable entries reproduce the exact validated C++ before rerunning the
original-library DUT, field utilities and large-packing native programs. Library
and test fingerprints and every TRACE match across hosts. Verification uses
`--shared-functions +define+UVM_NO_DPI` and native `-O0`; it is not full UVM or a
performance measurement. First UVM entry checks used the frozen test pathname,
which changed `__FILE__` strings and correctly prevented native reuse. Rerunning
with the original canonical test path reproduces the entire input byte-for-byte
before reuse. The old failed candidate and rejected checks are retained.

Updated entries: `~/vibe-coding/dsim-test/bin/dsim` and
103 `/apps/EDAs/own/dsim/bin/dsim` / `/apps/EDAs/own/dsim/dsim`.
See `release-groups.json`, `cross-platform.json`, `cross-uvm.json`, host receipts,
`sanitized-uvm-packing.json` and the current same-byte capability gaps in
`current-gaps.json`. RAL/VIP and all UVM combinations are not certified by these tests.
