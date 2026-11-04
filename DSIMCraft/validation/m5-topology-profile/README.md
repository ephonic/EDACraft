# Fixed topology behavioral profile

Complete current-runtime real design (128 golden) and feedback100k, isolated
counter instrumentation. This is not a timing result. Current/old complete
normalized preprocessor streams match; the real baseline whole C++ also matches
the actual adopted gate-source compiler output.

At nonzero times, real publishes 61,148,204 times, 21,057,826 unchanged;
40,090,378 changes scan 61,209,513 watchers, including 11,851,282 already not
waiting. Feedback scans 18,545,776, including 4,615,892 not waiting. Both have
zero generation/edge exclusions and all scans are fixed any-edge. The full
initialization/nonzero counts and final degree histograms are retained.

`verify.py` checks all raw artifact/archive hashes, exact instrumentation,
complete preprocessor identity, source/binary/golden identity and counter
relations. `profile-verified/` contains the raw programs, binaries, output and
preprocessor streams. Archive SHA256 is in `profile-archive.json`.

Counters motivated the separately rejected fixed-any flag experiment. Counts
alone do not imply instruction cost, CPU saving, or safe event elimination.
