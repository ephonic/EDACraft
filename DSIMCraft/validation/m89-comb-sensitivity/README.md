# M89: static bit sensitivity in specialized combinational processes

Implementation: `6e3e2101486f9c8573f1ef959dcf42796bfe2e84`; final test source: `8529cbb9f99df793a4bee720e3c914a262533198`.

`always_comb` / `always_latch` now accept static partial writes and reads of the same vector without a whole-word assignment. Lexical read prefixes include nested function bodies; static write intervals are removed from sensitivity. Existing expression waits compare the remaining slices, including X/Z changes. Whole-variable partition dependencies and writer-conflict checks remain conservative. Dynamic partial-write feedback without a whole-variable store continues to produce an explicit diagnostic. Writable ref footprints are not refined here. RTL/gate parsers and waveform encoders are unchanged.

The newly archived original `overlap48_hand` DUT/TB already passes M88; its 196 deterministic 48-bit dual-output observations are frozen in `tests/comb_sensitivity/reported`. M89 adds it to permanent regression alongside the new static feedback capability.

Validated:

- Nine models, 35 complete ordered captures across serial, time wheel and parallel execution, eight failed predictions/rollbacks, six illegal-source rejections. Actual parallel partition count is two.
- Actual VCS W-2024.09_Full64 on 10.131.254.103: nine complete stdout sequences match. Eight models have 729 common dumped bits; every common bit's complete settled timeline matches with no tail exclusions. Native-only bits are explicitly listed in `vcs-check.json` (19,828 array bits). VCS omitted arrays from text VCD even with explicit word dump requests. `memory_read` has no common VCD declarations: its complete word/wake stdout is checked, and its ordered wave is compared across native backends, rollback and sanitizer runs. Do not describe those array waveforms as VCS-aligned.
- Twelve actual ASan/UBSan programs, ten complete generated-C++ identities from the sanitizer compiler, six sanitizer compiler rejections; full ordered streams and stdout match native.
- Five affected old CTest groups pass: function effects, REPORT2, whole/partial combinational writes, indexed selects, specialized always. The initial specialized-always run expected the newly legal static feedback to fail; that obsolete negative was removed, its positive semantics are covered here, and the group passed again. Initial and final logs are retained.

`verify.py` checks source identity, complete stdout and all common VCS bits. `run-sanitizer.py` builds and executes instrumented generated programs. `generated-sha256.json` contains all 35 native generated-C++ hashes. `source-package.json` records the final source archive and every packaged file hash. Stable/Linux verification and installed-entry scripts compare complete new-group C++/stdout/ordered waves; `collect-evidence.py` stages only selected logs, waves, sources and metadata, excluding executables and generated C++.

Local publishing began before the source commit with the final compile inputs in a dirty tree; its metadata records that starting HEAD. `verify-release.py` additionally verifies every frozen input and all tracked compile inputs against the final implementation/test commit above. The local publisher's input set does not enumerate the older `tests/always_sv/regression.py`; that corrected suite is separately tested and included in the final Linux source manifest.

The first Linux publication was stopped before activation after the obsolete negative was found in its frozen test source. A new source package and release rebuild use the corrected suite. The stopped attempt did not activate either installation. The final release below passed acceptance and is active.

Both stable installations passed acceptance and are active:

- macOS: `/Users/yangfan/vibe-coding/dsim-test/releases/20261025T042058778669Z-e459f8db880c`; entry `~/vibe-coding/dsim-test/bin/dsim`. All 69 publisher checks pass. Binary SHA256 `bea46ca55fe5336e552ef36c9052b2592b1df887ab87da85e451dad75102ef1e`; source SHA256 `e459f8db880cb99301b0e3545f9921992d63c1f272447db8f2e69c6df3e2c43d`. All frozen inputs and runtime headers verify, with source commit verified separately as described above. All 35 complete C++ files, ordered waves and outputs match native. The actual installed entry recompiles static/functions/memory_read/reported with identical complete C++ and byte-for-byte VCD.
- Linux: `/apps/EDAs/own/dsim/releases/20261025T042512Z-8529cbb`; entries `/apps/EDAs/own/dsim/bin/dsim` and `/apps/EDAs/own/dsim/dsim`. All 9 groups pass, including the parser and gate-source suites. Binary SHA256 `0e9432d929b44b9ce4458bf122d27812fa05076b334272fda03718e3fec08af3`. All 1,308 source hashes, all 35 complete C++ files, ordered waves and outputs match macOS. After sourcing `/apps/EDAs/syn.bash`, the actual installed entry recompiles the same four models with byte-for-byte VCD equality.
- Final Linux source archive SHA256 `820d0ca0f95fc958439d87f427994d63820e3c73174974aa3ca9bb48a1385caf`.

No performance benchmark or VCS-wide functional parity claim is added.
