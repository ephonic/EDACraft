# Contact-z refinement and half-time-step study

Three new complete 60 ps MoS2 pulses passed independent physics and every-step
charge/current ledger checks. They complete the second local contact-z mesh and
a two-grid, two-time-step sensitivity matrix. Spatial/temporal qualification is
reported separately from successful solution and conservation.

## Frozen study

All cases retain the tested optional MMD Newton-preconditioner ordering,
representative homogeneous MoS2 material/trap/contact parameters, the same three
20 ps drive phases, and exact 5 nm electrode bounds. x/y remain 65/9 nodes.
Only cells within 1.25 nm of the fixed contact endpoints are bisected in z.
The three z levels contain 65, 81 and 113 nodes, with all inherited nodes kept.
No contact flux or charge rescaling is applied.

This study newly runs local-z level 2 with 128 steps/phase, and levels 1 and 2
with 256 steps/phase. The 128-step base and level-1 pulses are inherited from
the [previous complete-pulse study](../20261106-full-pulse/README.md); they are
not counted again as new simulations. Nonlinear tolerance is `1e-12`, and the
verified true row-scaled linear max-norm limit remains `1e-14`.

| New case | Grid | Steps/phase | Dynamic steps | Seconds | Peak process RSS (MiB) | LU factors | Refreshes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| local_z2_n128 | 65 x 9 x 113 | 128 | 384 | 713.85 | 1472.15 | 2 | 0 |
| local_z1_n256 | 65 x 9 x 81 | 256 | 768 | 636.57 | 703.55 | 2 | 0 |
| local_z2_n256 | 65 x 9 x 113 | 256 | 768 | 1532.47 | 1467.24 | 2 | 0 |

The cases ran serially with one BLAS/OpenMP thread and the unchanged SI float128
native extension. These resources include added diagnostic output, harmonic
initialization, all nonlinear solves and output encoding; they do not establish
a performance advantage between different grids or time-step counts.

## Independent audit

- **3 new full pulses, 1,920 dynamic steps and 12 full field checkpoints**,
  at initialization and 20/40/60 ps. The prior accepted state accompanies each
  dynamic field checkpoint. Full fields are not audited at every time step.
- **2,135,485 independent physics and ledger checks**,
  rebuilding carrier statistics, finite-volume bulk/sheet equations, contact/gate
  charges, trap BE kinetics, displacement currents and integrated charge balance.
  All scalar time-step ledgers and all 1,923 accepted linear diagnostic records pass.
- Atomic phase-end exports exactly match the final trajectory fields; the
  incremental accepted-linear journal exactly matches final linear records.
- Six corruptions are rejected, including an interior fine-step ledger,
  wrong dt, wrong mesh, excessive true linear residual, bulk field and gate bias.
- Inventory/linear-index transformations are reversible to the sealed auditor
  AST; physical formulas and gates are unchanged. Existing 215 targeted tests
  are inherited and were not rerun. No numerical product code changed.

## Spatial changes on fixed common nodes

All spatial increments below use the same original **65 x 9 x 65** support,
including the same x/y nodes. This avoids comparing maxima over different
sample locations. It is not a uniform error bound over unsampled fine nodes.

| Time (ps) | Base to local-1 bulk potential change (mV) | Local-1 to local-2 change (mV) | Increment ratio |
| --- | ---: | ---: | ---: |
| 0 | 1.290565 | 0.674118 | 0.522343 |
| 20 | 1.562807 | 0.816192 | 0.522260 |
| 40 | 1.215042 | 0.634640 | 0.522319 |
| 60 | 1.384013 | 0.722897 | 0.522319 |

The original normalized observable set/scales and difference/ratio limits
(`0.01`, `0.7`, roundoff cutoff `1e-8`) are retained for this local-grid
diagnostic. **50 / 54 local metrics pass**.
The following metrics fail:

- `0_dielectric_phi_V`
- `1_dielectric_phi_V`
- `2_dielectric_phi_V`
- `3_dielectric_phi_V`

The [maximum-change locations](spatial_hotspots.json) lie at the fixed contact
endpoints `z = +/-2.5 nm`, on the first interior x node about `0.12045 nm`
from a source/drain plane. This is observed at all four saved times for both
spatial increments. These locations guide the next contact-edge x/z study;
they do not by themselves establish an error bound or prove a boundary defect.

These are local-refinement diagnostics; global spatial acceptance failures
remain open. Refinement away from the contacts, including independent x/y/z
and joint refinements, is not replaced by this local study.

## Half-dt changes

The original dt is 0.15625 ps; half dt is 0.078125 ps. Values below compare
the full saved fields on each fixed mesh at the same 20/40/60 ps observations.
The initial state is exactly identical between the two dt runs on each mesh.
All 385 common scalar observation times match within `1e-24 s`.

| Time (ps) | Local-1 sheet potential change (microV) | Local-1 bulk potential change (microV) | Local-2 sheet potential change (microV) | Local-2 bulk potential change (microV) |
| --- | ---: | ---: | ---: | ---: |
| 20 | 6.23399 | 6.23399 | 6.23211 | 6.23211 |
| 40 | 10.3153 | 10.3153 | 10.3123 | 10.3123 |
| 60 | 6.62324 | 6.62324 | 6.6216 | 6.6216 |

The [common-support spatial/time scale comparison](spatial_time_scale_comparison.json)
separately compares local spatial increments and half-dt changes. The audit also
records the change in spatial increments after halving dt and the mixed
space/time difference. Two dt values do not measure temporal convergence order,
and a small field difference alone does not qualify all terminal observables.
At least a third time step and the remaining spatial studies are still needed.

## Full-trace current comparison

The new NumPy-only `benchmarks/sheet_refinement_trace.py` compares scalar states
at all 384 common accepted-step ending times. The physical audit separately
checks that the initial states are identical. The tool compares each coarse BE total current
with the average of its two fine substeps over the same physical interval.
This includes the gate-drive charge impulse. Conduction currents are additionally
compared at common ending times; cumulative terminal charge is compared at all
common observation times. No solver/native extension is imported by this tool.

| Local z level | Max interval-average total-current change (A) | Max common-ending-time conduction change (A) | Max cumulative total-current charge change (C) |
| --- | ---: | ---: | ---: |
| 1 | 1.59479e-08 | 2.54184e-08 | 5.31029e-21 |
| 2 | 1.59403e-08 | 2.53885e-08 | 5.31195e-21 |

The [complete trace comparison](trace_temporal_comparison.json) records terminal,
phase and time-step locations of maxima, signed cumulative integrals and fixed
normalizations. Fourteen new postprocessing tests passed, covering initial and
later-phase gate impulses, interval averaging, cumulative charge, error location,
mesh/drive mismatch, missing phases, invalid dt, nonfinite data and JSON/NPZ
loading. These are separate from the inherited solver test count.

## Next numerical checks

1. Add 512 steps/phase on a fixed local mesh, using the same 60 ps drive, to
   obtain three temporal resolutions. Compare both phase-end fields and full
   matched-interval current traces before estimating an order.
2. Refine the contact endpoint neighborhood further in z and independently in
   x, retaining exact electrode bounds and common-node observations. Check
   whether the bulk-potential maxima move or shrink without changing the
   original scales, limits or contact flux definitions.
3. Repeat the remaining independent-axis and joint spatial studies. Local
   contact refinement cannot replace the original global spatial acceptance.

## Replay and evidence

Exact tested drivers and nested mesh coordinates are included in
[reproduction](reproduction/README.md). The replay drivers preserve the original
physics and add incremental linear diagnostics plus atomic phase-end JSON/NPZ,
so later failure retains earlier accepted evidence. These exports are not
solver restart files.

See [full independent audit](independent_audit.json), [frozen policy](policy.json),
[resources](resources.json), [tool checks](auditor_tool_checks.json),
[source/archive identities](PROVENANCE.json) and [file hashes](MANIFEST.json).
Raw full fields and all step logs remain in the archive identified by provenance.
The tagged release and production deployment are unchanged. Material calibration,
full logic/memory qualification, quantum transport and Sentaurus equivalence are
not established by this numerical study.
