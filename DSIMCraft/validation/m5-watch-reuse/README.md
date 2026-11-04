# Reuse resolved fallback watches — not adopted

This independent candidate keeps `CompactSignal` at 48 bytes. Fixed any-edge
watch lists contain ordered process IDs; first dynamic/edge registration, alias
or extra driver converts those IDs to the existing resolved `Signal` fallback's
`watches`, preserving duplicate entries and slot indices. No new container or
tag is added to a net slot. The preceding rejected 56/64-byte, scalar-read and
queue-cold patches are absent.

Complete 300,909-cell real design, 128/128 golden on every run, and 100k flip-flop
feedback; GCC11.5/C++17/O2, fixed CPU0, one warmup each and five alternating serial
pairs. Shared host, unlocked frequency. Real median paired CPU saving **2.74%**;
feedback **−5.76%**, with all five feedback pairs slower. It fails both
preregistered limits (real ≥3%, feedback regression ≤3%), so there was no
independent repeat or adoption. No new VCS timing ratio.

The isolated candidate passed local 38/38, including duplicate order, stale
dynamic slots, conversion before/after reusable checkpoints, prediction
commit/reject, aliases and extra drivers. Three actual ASan/UBSan binaries cover
promotion, compact nets/parallel/delays, and module paths. Actual CLI-generated
eight-stage timed internal nets promote while path events remain pending;
rejected replay preserves complete decoded ordered/settled waves and observer
state relative to the uncompressed baseline using identical run boundaries.
Twelve valid ordinary-RTL macro combinations have identical complete normalized
preprocessor streams. This is isolated local correctness, not a production or
two-platform acceptance claim.

`verify.py` independently checks raw CPU/RSS, exact sources/binaries, every
golden output, all evidence hashes, sanitizer symbols, preprocessing, and full
timed wave streams. It also checks the unchanged accepted production/parser/
original waveform dependencies against the preceding SDF snapshot.

`screen-verified/` and `local-verified/` preserve raw artifacts. Archive paths and
SHA256 are in `screen-archive.json` / `local-archive.json`. Source reconstruction
uses the unchanged SDF production archive plus the frozen header/CMake/test and
rewrite script. `decision.json` is the independent rejection record. Do not
re-run the mutating verifier in this sealed evidence directory; use a copy.
