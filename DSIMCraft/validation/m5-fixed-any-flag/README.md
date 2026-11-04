# Fixed any-edge property flag — rejected after independent repeat

One cached flag occupies existing padding; original 48-byte compact net,
16-byte Watch, vector/order/duplicates, driver and scheduling semantics remain.
No preceding rejected optimization is included. Default production is unchanged.

The qualifying five-pair screen measured real median paired CPU saving 4.07%
(5/5 faster), feedback 1.81%. The independent seven-real/five-feedback repeat
uses exactly the same frozen sources/binaries, opposite starting order:
real **1.86%**, **4/7** faster; feedback 1.96%. It fails both real requirements
(≥3%, ≥5/7). All samples are retained, including 11.18/9.75 seconds. Shared
host, unlocked frequency, CPU0, GCC11.5/O2, full 128 golden every real run.
No new VCS timing, production adoption, or additional retries.

Local correctness: 41 CTests, then two canonical test-path checks; eleven actual
compiler whole SDF sources exactly match the intended runtime rewrite; twelve
ordinary RTL full preprocessor streams match. Four actual ASan/UBSan kernels
and eight actual generated boundary/replay programs pass. An eight-stage SDF
internal connection changes from fixed to dynamic waiting with timers pending;
complete ordered/settled waves and observer output match baseline/rejected
replay. There is no full Linux regression or sanitized compiler claim.

`verify.py` checks raw timing/golden and source/binary identities, all evidence
manifests/archives, actual sanitizer symbols and wave streams, and unchanged
production/parser/prototype files. `decision.json` records rejection. Original
local archives are retained; `generated-verified/` supplements generated
sources/noninstrumented waves omitted by the earlier minimal archive selection.
That first verification failure is retained in `verify-initial-missing-evidence.log`.
The first incorrect test assertion and its corrected final run are also retained.

The complete candidate source archive SHA256 is
`b96586be225a7e7166dbd0999590581d5c8eb6eb84f3c14b679787fcd25e8862`.
Prepared `linux.py` is deliberately not run after the repeat failure.
