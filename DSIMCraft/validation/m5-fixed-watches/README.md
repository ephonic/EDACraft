# Fixed-watch compression / alignment screen — not adopted

`verify.py` independently reconstructs every candidate from the frozen accepted
LUT program, checks source and binary identities, recomputes raw CPU/RSS and
paired statistics, and checks every full golden output. `decision.json` records
the rejection. No candidate changed the default runtime.

Before timing, `screen.py` and the frozen plan declared four variants: original
48-byte net slots, compressed fixed watches with 56-byte slots, compressed
64-byte aligned slots, and original watches with 64-byte alignment as a control.
All use GCC 11.5, C++17/O2, CPU 0, one warmup per binary and five rotating serial
rounds. The host was shared with unlocked frequency. Loads are the complete
300,909-cell real design with all 128 golden outputs, and 100k flip-flop feedback;
both have zero delay and no waveform recording. The baseline reuses the exact
accepted binary from the preceding queue experiment, checked by SHA; the queue
patch itself is absent. No scalar-read patch is included.

| Variant | Real median paired CPU saving | Feedback median paired CPU saving |
| --- | ---: | ---: |
| Compressed 56 | 6.04% | −8.06% |
| Compressed 64 | 6.18% | −11.52% |
| Alignment only 64 | 5.08% | −11.35% |

All three improved the real design in 5/5 pairs and regressed feedback in 5/5.
Each fails the preregistered feedback regression limit of 3%. None qualifies for
the independently required seven-real/five-feedback repeat or production
adoption. These are measured paired samples, not a general simulator speedup.
There are no new VCS timing runs or VCS ratios in this batch.

The compressed-56 isolated implementation also passed local 38/38 tests. A new
test covers duplicates, stable dynamic slots, stale generations, snapshots
before/after the first conversion, prediction commit/reject, aliases and extra
drivers. Actual CLI-generated eight-stage SDF internal nets exercise a dynamic
observer first added while path deliveries remain pending. A rejected prediction
crosses that first conversion; all decoded ordered/settled DWF metadata/events
and final observer state equal the uncompressed baseline using the same
`run_until` boundaries. `verify.py` compares the complete decoded streams without
filtering events. This is candidate correctness evidence; the two 64-byte
variants have no broad correctness/sanitizer/two-platform claim. Failed screening
does not justify their adoption.

Frozen evidence:

- `screen-verified/`: 169 original files plus manifest, complete generated C++, ELF
  programs, warmups, all raw time/stdout/stderr, compile logs and result/protocol.
- `local-verified/`: candidate header/compiler, promotion test, 38-test logs and
  complete generated timed programs, binaries, waves and replay output. Includes
  the unchanged accepted header and pre-screen plan.
- `screen-archive.json` and `local-archive.json`: immutable `/tmp` archives and
  hashes; remote screen root `/tmp/dsim-fixed-watches-screen-1018-aUPoJe`.
- `verify.py`: additionally checks that accepted production implementation,
  parser files and original waveform dependencies still match the preceding
  frozen SDF production snapshot.

Next experiment: avoid increasing the compact net slot and extra indirection by
reusing mutually exclusive fixed/general watch storage, then measure both loads
afresh. No smaller representation is assumed faster before that experiment.
