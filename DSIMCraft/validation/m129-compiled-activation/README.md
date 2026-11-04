# M129: bounded native process activations

The generator recognizes single-wait `always` / `always_ff` processes whose body has a forward-only control-flow graph. It emits native branches instead of repeatedly interpreting the PC. One entry guard proves the entire activation fits the remaining execution budget; every original instruction still charges a step before its effects. The original PC closure remains the cold fallback for partial activations and small budgets.

Eligibility comes from lowered control flow and feature requirements. Loops, embedded case dispatch, internal suspension, complex process controls, side effects and unsafe expressions retain their existing paths. There are no module-name, CPU-instruction or program-content predicates. Clang and Intel use the path by default; GCC retains the previous default until separately measured. `DSIM_REFERENCE_COMPILED_ACTIVATION` is the comparison switch; `DSIM_EXPERIMENTAL_COMPILED_ACTIVATION` allows explicit experiments on other compilers. The IR lists eligible `compiled_activations`.

CPU has seven eligible processes and AXI4 has two. CRC and muldiv have none: this change does not claim to accelerate their native arithmetic loops. Signal publication, FIFO enqueue order and NBA commit order are unchanged.

The implementation is frozen at `bafe1875f69bf60a1041257bf1eb943cf59da9c9`; all 1711 packaged source files match Git (`source-proof.json`). Complete measurement, regression and release identities are recorded beside this document. The pre-existing exhausted-budget exception can lose a popped process; resume comparisons that reproduce reference errors are reported separately from successful continuations.

The CPU diagnostic prefix preserves `PROFILE 200000000 5767258 1604582946171822610`. It replaces 932050 of 2040717 interpreted PC instructions with native control flow across 140006 activations, leaving 1108667 PC iterations. All 921690 signal publications have the same hash including timestamp, logical instruction position, signal ID and both value planes; Ready pushes/pops remain 957631. These are software work counts, not hardware retired-instruction counts or a predicted CPU-time gain.

Both platforms exercise ten models: 100 ordered/settled captures, 2630 budget comparisons, 20 accepted/rejected predictions and 1248 FIFO batch states. Of 720 bounded replay comparisons, 117 reproduce pre-existing reference errors; they are not successful continuations. Two generated programs pass ASan/UBSan. Linux also passes the thirteen existing kernel CTests, plus parser/native DB, compiler options and gate source checks on each installation.

The two new TRACE probes agree with VCS. Its default frontend rejects declaration initializers on `always_ff` targets in the branches fixture; that probe uses the explicit `-ignore initializer_driver_checks` option, and the initial failed compile remains recorded remotely. This checks the optimized execution behavior with that vendor check disabled, not default frontend acceptance. Vendor-generated code and binaries are excluded from public source/evidence archives.

`development.json` is an earlier screen: a separate vendor probe compilation overlapped part of it. `linux-full.json` is the final comparison of already-built installed programs, after all our Linux builds/checks finish. Default installed `.text` matches the experimental candidate; the reference control `.text` matches frozen M126. CRC and muldiv candidate/reference `.text` are identical, so their timing differences are noise rather than optimization gains. Mac host contention is uncontrolled; no portable Mac speedup is claimed.

## Final installed full-workload comparison

Linux CPU 25; Intel 2026.1, strict floating point, O3/xHost/IPO; one warmup and three rotated complete runs per variant. All original sources and workloads are unchanged. CPU time and wall time are recorded separately in `linux-full.json`; the host is shared and frequency/load is uncontrolled, including one 10.30s CPU candidate outlier retained in full.

| Complete workload | Frozen M126 CPU (s) | Installed M129 CPU (s) | VCS CPU (s) | Interpretation |
| --- | ---: | ---: | ---: | --- |
| CPU | 9.31 | 8.92 | 5.68 | 4.19% less CPU time; still 1.57 times VCS |
| CRC | 3.06 | 3.05 | 3.90 | identical native text; no gain claim |
| muldiv | 7.34 | 7.24 | 6.87 | identical native text; no gain claim |
| AXI4 | 0.17 | 0.17 | 0.57 | short workload; no gain claim |

Both stable installs regenerate identical C++ for all four full workloads, match every expected complete result, and load the same eight runtime headers. Mac release `20261027T101502253921Z-491a233cc5fd` uses SDK Clang; Linux release `20261027T101527Z-bafe187` uses Intel for frontend and models, and both Linux entry points resolve to the same binary. Original PC/NBA/notification semantics remain the reference; generic embedded case dispatch, `always_comb` DAG fusion and static NBA propagation are still future work.

The self-owned raw archives (14290 Mac members, 14392 Linux members) are member-verified and copied to both installations under `evidence/m129-compiled-activation`. `mirrors.json` checks the four installed archive hashes. `audit.py` cross-checks both source/installations, regression totals and all 48 final complete run outputs/timing logs against the archived originals. The archives contain DSIM-generated programs and the two VCS probe input/output records, with no vendor-generated code or binaries.
