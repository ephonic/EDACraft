# Bounded uniform y33 capacity probe

**The y33 initial/first-BE probe timed out after 3,600 seconds.**
It saved no initial field. The
original 26 y9/y17/y33 metrics remain **unevaluated**. The
[raw exception](failure.json), [failure audit](failure_audit.json),
[prelaunch policy](policy.json), [checker replay](auditor_tool_checks.json),
[identities](PROVENANCE.json) and [hashes](MANIFEST.json) retain the outcome.

The preceding fresh MMD y9 control completed one backward-Euler step and two
full fields in 103.04 s, with peak process RSS
860.44 MiB and maximum nonlinear residual
3.5365352e-15. Its **387,923 independent physical and
ledger checks pass**, and all eight corrupted variants are rejected.
Its initial full state, first two scalar trace entries and linear diagnostics
match the inherited MMD full y9 run after the sole expected first-BE cache
invalidation flag adjustment. First-BE full-field parity is unavailable from
the inherited full run and is not claimed.

## Frozen capacity experiment

Both cases use x65/z113, uniform nested y9/y33 coordinates, MMD ordering,
dt 0.15625 ps, the same representative isothermal MoS2 material, traps and
finite contacts, and unchanged SI float128 native code. The y17 short
comparison is identified in the [preceding cache report](../20261106-cache-profile/README.md).
Only the y selector changes from that sealed explicit-release driver.
The y33 mesh has 242,385 bulk nodes and
2,145 sheet nodes.

Jobs run serially with one BLAS/OpenMP thread and 48 GiB address space.
The y9 control retains a 900 s wall/CPU and 6 GiB peak-RSS audit gate.
The y33 probe has a separately declared 3,600 s wall/CPU and 32 GiB RSS
budget. Nonlinear `1e-12` and true row-scaled linear max-norm `1e-14`
tolerances are unchanged. The detailed exception records which condition
ended this attempt; resource failure alone does not establish physical
divergence. Older memory/time failures remain preserved.

The last sampled y33 observations reach 3599.49 s
elapsed and 2584.88 s process CPU; the maximum
observed process high-water mark is 10981.00 MiB.
These sampled values are **lower bounds**, not a final peak or completed
runtime measurement. 0 atomic y33 field checkpoint(s) survive;
they receive zero completed-probe or convergence credit. All raw partial
outputs remain in the sealed archive. Intermediate checks also receive
zero additional simulation credit.

## Reproduction and remaining work

Replay [these drivers and mesh](reproduction/README.md) under the recorded
policy. The prelaunch checker exactly replayed the inherited y17 physical
audit, rejected eight corruptions and reproduced the original metric and
dense-projection results. No acceptance formula or gate was changed after
the outcome.

Numerical source is unchanged. The 223 solver regressions are inherited
by exact source hashes and were not rerun. Candidate, test, native,
protected original source and production identities were reverified;
all owned workers have exited.

The preceding [full y17 pulse](../20261106-first-full-y-pulse/README.md)
retains its accepted 60 ps physics audit. Complete y33, full three-grid y
qualification, fine-grid temporal refinement and joint space/time
qualification remain open. The next step is to isolate the finer-grid
linear-solve cost before another long trajectory. This representative
classical case does not qualify arbitrary 2D logic/memory, quantum transport
or full Sentaurus equivalence. No native rebuild, commercial run,
production deployment or release was performed.
