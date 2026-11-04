# M113 generated-code and compiler experiments

The adopted change is an optional, repeatable [GCC PGO workflow](../../docs/pgo-models.md), implemented by `scripts/build_pgo.py` at `9692d0f81114f5af2ed92672a75698a84bf9d7c4`. All three generator/runtime candidates below were withdrawn. The stable simulator remains M111; restored default output for all four original workloads is byte-identical (`restored-default.json`). This iteration does not claim default-runtime acceleration or general VCS feature parity.

## Separate GCC PGO measurement

`pgo.py` uses frozen M111 C++ and unchanged complete CPU, CRC, muldiv and AXI4 inputs. Each model trains once on the same complete workload evaluated afterward. GCC 11.5 uses `-std=c++17 -O2 -pthread`, with `-fprofile-generate` then `-fprofile-use`; missing/mismatched profile data is fatal. All compilations finish before measurement. Frozen M111/PGO/VCS run on CPU 0 with one warmup and three rotated rounds. VCS is W-2024.09_Full64. Shared-host load/frequency is uncontrolled; all samples, including warmup outliers, are retained. This is not a PGO measurement of a new generator, nor a claim about untrained inputs.

| Full workload | M111 CPU / wall (s) | PGO CPU / wall (s) | VCS CPU / wall (s) | CPU reduction | PGO/VCS CPU |
| --- | ---: | ---: | ---: | ---: | ---: |
| CPU | 15.11 / 15.94 | 13.01 / 13.22 | 5.84 / 9.04 | 13.9% | 2.23 |
| CRC | 4.42 / 4.46 | 3.66 / 3.68 | 3.94 / 6.95 | 17.2% | 0.93 |
| muldiv | 11.06 / 11.10 | 9.91 / 9.94 | 6.89 / 11.70 | 10.4% | 1.44 |
| AXI4 | 0.24 / 0.24 | 0.21 / 0.21 | 0.57 / 3.37 | — | — |

The short AXI4 case is a control, not a throughput claim. VCS wall time includes startup. `pgo.json` retains samples, exact source/executable/profile identities and medians. `pgo-audit.json` independently recomputes 48 original time logs, verifies complete outputs, and checks frozen M111/VCS executable identities. Training adds an instrumented build/run and a feedback build; no end-to-end speedup including that extra work is claimed.

## Withdrawn generator candidates

1. Sequential switch fallthrough retains every step and suspension PC. Two-round screening without warmup shows CPU 15.10→15.425s, CRC 4.425→4.865s and muldiv 11.09→11.72s. `initial-screen.json` records independent linear/local/combined variants. Reference-mode machine code differed for some non-CPU cases, so that first screen does not isolate local caching by itself. Fallthrough was withdrawn; M109 had also rejected related dispatch approaches.
2. After restoring original dispatch, cache only private automatic function locals surrounding native loops. The reference `.text` matches M111 for all four workloads; candidate `.text` changes only CRC. CRC baseline/reference/candidate CPU medians are 4.43/4.44/4.60s. The larger source and fewer generic stores did not produce faster execution. See `locals-isolation.json`; warmups and all wall samples are retained.
3. Count native-loop iterations locally against one remaining-budget calculation, then commit exactly the completed step count before writeback/PC fallback. All original observation and four-state guards remain. Full M111/candidate/VCS warmup plus three rotated rounds shows CRC 4.41→4.40s (0.23%); CPU/muldiv/AXI4 `.text` is unchanged. This is insufficient evidence to adopt. `budget-measurement.json`, `budget-binaries.json` and `budget-audit.json` retain the 48-run result, byte identities and independently recomputed logs.

The budget candidate passes 454 exact budget/state/resumption comparisons, 16 VCD captures and four prediction outcomes (`budget-development.json`); eight affected groups pass (`budget-affected.json`), including real two-partition integral-loop tests and process controls. Three generated programs plus the uint64-boundary kernel pass ASan/UBSan (`budget-sanitizers.json`). Correctness alone is not evidence of speed. The runtime/generator were restored and rebuilt after these experiments.

The three `withdrawn-*.patch` files are review/reproduction artifacts, not current product changes. Apply the relevant patch to pre-experiment `5f5c5e554f2bdcf5d0e76a8648079b13f450ad87`. To reproduce the budget tests, copy `budget-candidate-tests/` to `tests/loop_budget/` first; its scripts intentionally use that original test location. `loop-budget-candidate.md` describes the withdrawn method. `screen.py`, `isolate.py`, `isolate-budget.py`, `prepare.py`, `measure-budget.py`, `affected.py` and `sanitizers.py` operate on these archived candidate inputs; regenerating with current main produces the restored M111 path.

## Workflow verification and installation

`pgo-workflow.json` records a real generated RTL model with automatic functions, X/Z inputs, two-state conversion, native loops and `$readmemh`. GCC training/feedback/verification passes, including paths with spaces, literal flags, a separate input working directory, existing-directory protection and recorded compile failures. The initial fixture placed an initialization before its referenced declaration; it was reordered before successful acceptance. `vcs.json` compares nine TRACE lines from plain/wave/PGO runs and 129 complete scalar-bit timelines against VCS. The unpacked training memory is explicitly excluded from this waveform selection. Only hexadecimal letter case is normalized in TRACE comparison.

The helper is installed separately at `~/vibe-coding/dsim-test/tools/build_pgo.py` and `/apps/EDAs/own/dsim/tools/build_pgo.py`. `install-mac.json` and `install-linux.json` verify the source-commit/script hash and unchanged stable-simulator hashes. The installed Linux helper trains and verifies the generated RTL again (`installed-workflow.json`). `mac-workflow.json` checks CLI/Apple-Clang rejection; GCC is unavailable on this Mac, so a full Mac GCC training run is not claimed. The CTest is registered only for GNU compiler builds.

Large raw logs, generated C++, profiles and complete waves are retained privately under each installation's `evidence/m113-generated-regions` directory. `raw-evidence.json` and `evidence-mirror.json` identify member-verified archives and matched copies; executables, proprietary vendor-generated code and user experiments are excluded. Original benchmark source hashes and frozen baseline identities are retained in `environment.json` and the prior M111 evidence. The observed gains apply to the measured PGO models; substantial scheduler/notification work remains, and generic process fusion is not implemented by these experiments.
