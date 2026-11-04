# M230 — runtime array streams and fixed string storage

Runtime bit streams use an MSB-first four-state byte sequence, retaining runtime
length independently of packed expression width. Array casts retain destination
shape instead of folding to one element. Segmentation handles wide words,
partial slices, empty queues, right padding, bounded queues and X/Z conversion.
All operands are evaluated once, with left-to-right value snapshots.

Fixed string arrays use text signals, text-preserving indexed reads/writes and
automatic activation storage. Dynamic indices, whole copies, input/ref formals
and concurrent delayed task outputs have native probes. Dynamic string arrays
and class fixed-array properties remain unsupported.

Fourteen models pass serial/shared/shared-wheel modes (42 full ordered captures),
five protected compile boundaries and two actual runtime cast-size errors.
Six sanitized frontends and native models pass with complete shared C++ and wave
identity. Five forced failed predictions pass equal-horizon full-wave comparisons.
Older strings and string subroutines pass 31/46 captures, four rollbacks each,
and 24/10 compile boundaries. The old blanket fixed-array rejection is removed;
the scalar-to-array argument rejection uses its current shape diagnostic.

All fourteen same-byte fixtures compile/run on VCS W-2024.09. Twelve outputs
match dsim. The ordering and side-effect capture probes retain their raw VCS
outputs as two explicit differences (vcs.json), not alignment successes.
Of five compile boundaries VCS accepts three (class-handle/associative stream
sources and dynamic string arrays) and rejects two. Both cast-size probes are
runtime rejections on both simulators. These are capability boundaries, not a
claim that every rejected source is invalid SystemVerilog.

Original attempts preserve their failures: early VCS probes used a deliberately
failing cast in an all-success wrapper; numeric probes replaced unsupported
unpacked %p display; four-state-only models exposed a nested runtime feature
guard, corrected before final regression; a negative had a stale diagnostic.
A string out-of-range method query is separate from the final positive fixture:
dsim returns an empty string, whereas VCS emits IOBA. This difference is retained.

Unchanged complete Accellera UVM 2020.3.1 with UVM_NO_DPI, all 181 file fingerprints
matching the earlier passing VCS oracle, now passes reg_map:2160 streaming/cast
and the fixed local string declaration in the bit-bash sequence. Normal and
sanitized frontends stop at uvm_phase.svh:2092: associative array arguments by
value/output are not implemented. No complete UVM native program/run_test pass.
Raw evidence: dsim-test/evidence/m230-array-streams. No performance/C910 claim.

Production 31b70e74 is pushed. Mac 20261103T171855349731Z-b3a4c2db51ac and
103 Intel 20261103T171924074799Z-b3a4c2db51ac are active. Each frozen release
passes five groups: 165 captures, 46 compile boundaries, four runtime errors
and mandatory parser/format/native DB checks. All 42 new C++ inputs match
development. Fourteen actual-entry C++ inputs/traces match across hosts after
native reruns and complete-wave checks. Both 103 aliases pass.
Both actual stable entries, using the unchanged 181-source library, reproduce
the associative value/output blocker without generating a complete UVM model.

The next output-map gap has a same-byte VCS reproducer in
probes/next-associative-output.sv. While its task waits, the caller retains the
original map; after return the output replaces it. VCS passes both observations;
dsim rejects the call. This remains a documented gap, not a passed dsim test.
