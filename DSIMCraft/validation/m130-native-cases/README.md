# M130: native case and implicit-sensitivity activations

The generator records constant scalar case selection and forward successors in the lowered IR. Bounded activations emit native transfers to those successors, including nested cases, instead of interpreting the PC after each branch. The same path now handles `always_comb` / `always_latch` bodies and their terminal rearm. Selection diagnostics retain their original instruction and runtime delivery behavior. Processes marked with other side effects remain excluded; nonconstant/wildcard case dispatch, loops, internal suspension and unsupported process features retain the PC path.

A whole-activation budget guard precedes execution. Every original instruction still charges its step before effects, including branch and wait instructions. Cold PC fallback handles partial activations and insufficient budgets. FIFO notifications, NBA order and every intermediate signal publication remain unchanged. Eligibility uses semantic/control-flow information, with no module-name, CPU-instruction or program-content predicates. Existing Clang/Intel defaults and GCC opt-in are unchanged.

CPU coverage grows from seven to thirteen processes; muldiv has one and AXI4 three, while CRC has none. The fixed CPU prefix preserves 5767258 logical steps, the all-signal state hash, all 921690 ordered publications (timestamp, logical step, signal ID and both value planes), and 957631 ready pushes/pops. Interpreted PC iterations fall from M129's 1108667 to 436016, with 1604701 native instruction charges across 308011 activations. These are software work counts, not a hardware instruction count or a CPU speedup percentage.

The new fixture covers nested cases, duplicate labels/branches, unique overlap diagnostics, signed labels, unknown selectors/data, clocked NBA and latch behavior. Eleven-model checks compare serial, time-wheel and parallel captures against the original interpreter, plus low budgets, checkpoint replay and prediction acceptance/rejection. The legacy exhausted-budget exception can lose a popped process; reference errors are reported separately from successful resumptions. A separate case oracle disables the host constant-case switch while retaining native activations.

Implementation is frozen at `fe0d61c90a694daae577d6709232de4621ecb878`. All 1712 packaged source members match Git (`source-proof.json`). Both installed entry points regenerate the same complete-workload C++ and match every expected result, with the same eight runtime headers. Generic DAG fusion, intermediate-publication removal and fixed NBA propagation remain unfinished.

The added generated C++ is 29830 bytes for CPU, 5629 for muldiv and 17153 for AXI4; CRC is unchanged (`coverage.json`). The final prefix's remaining interpreted instructions are 120001 and 99998 in the two timed testbench processes, and 60003/60000/48006/47997 in four continuous memory-read paths. These identify remaining interpreter work, not exclusive CPU-time shares. Signal notification and ready-queue counts are unchanged, so this does not complete static propagation or scheduler fusion.

## Final installed comparison

Linux CPU 25, Intel 2026.1 O3/strict/xHost/IPO; one warmup and three rotated complete runs per variant. These are already-built installed programs, measured after all our Linux compilation and semantic checks finish. CPU and wall time remain separate in `linux-full.json`. This is a shared host with uncontrolled frequency/load; all samples and outliers are retained.

| Original complete workload | Frozen M129 CPU (s) | Installed M130 CPU (s) | VCS CPU (s) | Interpretation |
| --- | ---: | ---: | ---: | --- |
| CPU | 9.13 | 8.94 | 5.89 | 2.08% less CPU time; 1.52 times VCS |
| CRC | 3.05 | 3.07 | 3.91 | identical native text; no gain claim |
| muldiv | 7.45 | 7.14 | 6.88 | 4.16% less CPU time; 1.04 times VCS |
| AXI4 | 0.16 | 0.17 | 0.59 | short workload; no gain claim |

The installed default `.text` matches the experimental prototype for all four models; frozen reference hashes match M129's final installed results. The earlier single-case candidate had no confirmed benefit; its full samples remain in `development-single.json`. The broader development screen is `development.json`, separate from the final installed comparison. No portable Mac performance gain is claimed.

Both platforms pass 110 ordered/settled/prediction captures, 2893 budget comparisons, 22 predictions and 1248 FIFO batch states. Of 792 replay comparisons, 117 reproduce existing interpreter errors; they are not successful resumptions. Mac controls/cases programs pass ASan/UBSan. Linux also passes the thirteen existing runtime kernel CTests, parser/native DB, compiler options and gate source checks. The sequential-label case oracle preserves all 103 ordered waveform events.

The original new case fixture compiles with VCS default checks. Adding the same dumpfile/dumpvars observer to both inputs yields identical two TRACE lines and all 77 settled bit timelines, including unknown selectors/data, signed labels, latches, NBA and unique diagnostics' value effects. Diagnostics' vendor-specific wording is not compared. Only the probe input, waveforms and stdout are archived; no vendor-generated code or binaries are copied into the repository or evidence archives.

Stable Mac release `20261027T141325792417Z-c26955c7866e` uses SDK Clang; Linux `20261027T141430Z-fe0d61c` uses Intel for frontend and models. Both Linux entry links resolve to the same binary. Installation hashes are recorded in `mac-entries.json` / `linux-entries.json`. All 1712 source members match frozen Git; Mac publisher's 726 input fingerprints match the frozen package despite unrelated untracked workspace files.

Both self-owned raw archives are member-verified and mirrored to both prefixes under `evidence/m130-native-cases`. `mirrors.json` verifies all four installed copies. `audit.py` checks source/install identities, headers, all semantic totals, every raw member and all 48 final full outputs/timing logs. `plan1017.md` records the implementation and remaining structural work.
