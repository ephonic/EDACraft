# Changelog

All notable changes to TCADCraft are documented in this file. Versions follow
Semantic Versioning, and dates use ISO 8601.

## [0.2.0] - 2026-08-11

### Added

- Calibration for HfO2 ferroelectric hysteresis,
  silicon trap stress/recovery, GaN Schottky nonlocal tunneling, 8 nm
  density-gradient confinement, and electrothermal avalanche breakdown.
- A pure-Python Sentaurus response-model loader for emerging-material
  calibration surfaces.  The IGZO/WSe2 synthetic response replay is explicitly
  marked as non-physical truth and rejects out-of-range gate-bias evaluation by
  default; the calibration artifacts now include separate positive- and
  negative-gate IGZO/WSe2 branches.
- A mixed-material calibration dashboard and release gate for IGZO/WSe2.  The
  dashboard separates the passed Sentaurus response replay, the passed IGZO
  full-DD tail-selector branch set, and WSe2 compact-contact diagnostics that
  intentionally remain diagnostic-only.
- A formal 22,113-node classical/electron-DG replay for the 8 nm non-planar
  double-gate FinFET, including threshold, current-ratio, convergence, and
  quantum-residual gates.
- A formal 2-D planar-nMOS Id-Vg/Id-Vd replay covering five bias branches,
  threshold voltage, subthreshold swing, transconductance, inversion charge,
  and terminal-current conservation.
- A formal 3-D freestanding four-side GAA nanosheet replay with four classical
  Id-Vg/Id-Vd branches and two electron-DG Id-Vg branches, including raw-sheet
  current, threshold, quantum-suppression, KCL, Poisson, and DG residual gates.
- Calibratable Schottky thermionic/nonlocal-tunneling contacts, reliability and
  trap models, GaN material defaults, and wrap-gate device construction.
- Electrothermal breakdown replay with avalanche-integral, hotspot,
  temperature-stop, and terminal-current conservation gates.
- Reliability, Schottky-contact, wrap-gate, analytic-limit, MMS-convergence,
  and coupled-solver regression coverage.
- Public density-gradient configuration from DOS masses and Sentaurus gamma
  factors, plus an explicit fixed material-interface distance closure.
- An opt-in analytic material-step Robin closure using explicit barrier-side
  masses, band offsets, gamma, and theta parameters (Sentaurus Eq. 250).
- An opt-in Gummel potential-form density-gradient PDE (Sentaurus Eq. 248)
  with the equation-250 material-step condition in the same fixed-point solve.

### Changed

- Newton is now the authoritative result on Newton-primary runs; a skipped or
  failed Gummel warm-up can no longer report false convergence.
- Coupled Newton includes Auger recombination and analytic derivatives, uses a
  mixed absolute/relative KCL guard, and retains carrier consistency after a
  converged solve.
- Density-gradient handling, nonuniform-grid edge metrics, contact-current
  extraction, adaptive continuation, and thermal stop-point refinement were
  hardened for nanoscale and high-field devices.
- High-drain GAA DG continuation now follows frozen basin-aware waypoints,
  retains the best true-residual polish result, and supports validated atomic
  state checkpoints without publishing intermediate continuation points.
- Newton Poisson now uses edge-length times node-control-width on nonuniform
  meshes, and Newton carrier continuity clips zero-mobility transverse
  half-cells at material interfaces exactly as Gummel does.
- High-dynamic-range 3-D continuity failures now retry carrier-state column
  scaling and row-only equilibration with mixed-precision refinement, while
  retaining the original float128 equation-residual acceptance gate.
- The public density-gradient interface-distance factor now also applies to
  the potential-form material boundary, and Python solve results expose the
  final Poisson residual alongside the quantum residual.
- Schottky contacts can model a first-order velocity-saturation bulk drop and
  a continuously closing nonlocal sub-barrier window; legacy behavior is
  unchanged when these options are omitted.
- Schottky/NLM contacts now support an explicit Fermi-level pinning slope
  parameter and a WSe2-oriented convenience adapter, while retaining the
  Schottky-Mott default.
- Added a WSe2 compact gate-controlled Schottky/NLM contact proxy seeded from
  the Sentaurus IGZO/WSe2 material-deck calibration diagnostics.
- WSe2 compact contacts now expose an opt-in hole branch for ambipolar
  high-drain diagnostics; the branch is disabled by default.
- WSe2 compact contacts also expose an opt-in ambipolar notch/filter kernel
  for high-workfunction/high-drain transfer-curve diagnostics.
- WSe2 compact contacts expose an opt-in post-valley recovery kernel for
  two-lobe transfer-curve diagnostics.  This improves the wf=4.9 eV,
  Vd=0.5 V targeted branches but is not marked as a full-device pass.
- Release checks can validate the mixed IGZO/WSe2 calibration dashboard using
  `scripts/release_check.py --mixed-material-dashboard <dashboard.json>`.
- Density-gradient convergence now has a physical quantum fixed-point residual
  gate with safeguarded Aitken relaxation and best-state recovery.
- Refined quantum meshes now reduce transport-Q mixing before a detected
  Gummel cycle is handed to Newton. A carrier block that is already quiet is
  advanced on an eight-iteration checkpoint cadence; convergence and final
  residual audits still require a simultaneous two-carrier checkpoint.
- Fixed-phi quantum continuity polishes now inherit the Q-mixing reduction
  selected by the outer cycle stabilizer. They no longer reset a contracting
  `x0.25`/`x0.125` state to the nominal mixing factor during the final equation
  audit.
- Multi-step fixed-phi carrier damping now references the immediately previous
  inner iterate while retaining the function-entry state only for transactional
  rollback. This removes an anchored false fixed point whose carrier updates
  could vanish with a nonzero density-gradient equation residual.
- Independent quantum-residual audits now distinguish strong contraction from
  a genuine plateau: contracting states receive one bounded checkpoint, while
  a three-audit plateau advances to the next Q-mixing level. The bounded
  damping spectrum now extends through `x0.0078125`, allowing stiff
  strong-inversion states to keep contracting before a Newton handoff; the
  Aitken floor scales to one percent of the active ceiling only below
  `x0.125`, after the current level has equation-audit evidence, so those deep
  levels are effective without perturbing ordinary continuation points.
- The potential-form density-gradient PDE now iterates its nonlinear
  Gauss-Seidel solve to a strict inner update residual (up to 64 sweeps), rather
  than returning after eight unconditional sweeps and leaking unresolved
  spatial modes into the outer Gummel fixed point.
- Quantum Gummel stabilization also detects a 24-step nonzero carrier-update
  plateau, in addition to alternating limit cycles. A plateau can reduce Q
  mixing while a lower level remains, but cannot force a Newton handoff at the
  terminal `x0.0078125` policy.
- A terminal Q-mixing cycle with a finite near-gate equation audit now receives
  one bounded damping-spectrum restart from its accepted state. This replaces
  the ineffective Newton handoff plus caller-level same-bias retry while
  retaining the original Poisson, continuity, and quantum residual gates.
- A monotone three-audit plateau at the terminal Q-mixing level can now invoke
  the same once-per-solve restart when it lies within 256 quantum tolerances.
  This closes the non-oscillatory path that previously bypassed the cycle
  detector and repeated expensive fixed-phi audits until `max_iter`; final
  equation acceptance criteria remain unchanged.
- Strongly unipolar quantum states may start the transactional final equation
  audit when eight simultaneous carrier checkpoints form a near-tolerance
  plateau within eight times the requested update tolerance. Acceptance still
  requires the checked undamped continuity solve and the unchanged
  Poisson/quantum gates, avoiding a roundoff-level pre-audit cycle without
  weakening result validity or auditing an ordinarily contracting trajectory.
  Until its Q gate passes, this plateau-only audit retains transport-Q
  progress but leaves n/p write-back to the outer damped iteration, preventing
  an undamped minority-carrier jump from creating a new cycle.
- Quantum Newton now freezes each lagged density-gradient potential across
  residual, Jacobian, and line-search evaluations, then refreshes it through a
  damped outer Picard step. Deep-depletion variables use an active set, while
  the remaining log-carrier blocks use adaptive trust bounds and RMS
  globalization with a strict worst-row guard.
- Potential-form DG uses a bounded 64-step fixed-relaxation polish and carries
  its accepted transport-Q state across bias points. The final 5 nm W-2024.09
  continuation reaches a `6.15e-8` quantum residual without changing the
  default density-form solver path.
- Material-side interface replays now retain the oxide and semiconductor nodes,
  derive interface charge occupancy from the actual dual control volume, and
  use the whole-edge oxide permittivity when the interface is node-aligned.
- Equation-250 gamma defaults now come from the non-solved barrier (`0+`) side;
  bulk equation-248 silicon gamma values remain independent.
- Potential-form transport quantum potentials persist across voltage steps,
  avoiding a density-form restart and oscillatory reconvergence at every point.
- Under Boltzmann statistics, equations (247) and (248) now share the same
  discrete density map; the independent potential PDE is reserved for Fermi
  statistics, where the equations are not algebraically equivalent.
- Portable problems above 2,000 nodes now use an internal banded-LU path for
  narrow structured matrices and ILU0-preconditioned GMRES for wider systems,
  instead of the unstable BiCGStab fallback.
- Quantum overflow protection is fixed at `16*kT/q`; it no longer changes with
  film thickness or mesh node count.
- Release builds no longer use host-specific `-march=native` instructions
  unless explicitly requested with `TCAD_NATIVE_OPT=1`.
- Portable builds default to the internal direct solver, avoiding BLAS/LAPACK
  symbol collisions when PyPI SciPy wheels are installed. System LAPACK is now
  an explicit source-build option (`TCAD_USE_LAPACK=1`).
- Native Windows now fails early with an actionable WSL2/Linux message instead
  of being misconfigured with Unix compiler and linker flags.

### Fixed

- Removed the post-Newton Poisson-only solve that could invalidate converged
  carrier/electrostatic consistency.
- Restricted carrier safety clamping to non-converged failure states.
- Corrected version metadata drift between the package and runtime module.
- Included C++ headers and sources in source distributions and corrected
  project URLs.
- Fixed a clean-environment segmentation fault caused by mixing system LAPACK
  with the private BLAS/LAPACK runtime shipped in SciPy wheels.
- Corrected semiconductor/insulator carrier control volumes and transient
  Newton residual scaling, eliminating interface KCL errors and frozen-block
  false convergence.
- Removed implicit thickness-switched density-gradient coefficient and
  interface-distance adjustments.
- Corrected cut-cell endpoint limits (`alpha=0/1`) and propagated ordered device
  region geometry into high-level cut-cell preprocessing instead of assuming
  every mixed-material edge crosses at its midpoint.
- Continuity linear solves commit only finite, row-residual-checked states.
- Final density-gradient equation audits now reject and transactionally roll
  back non-finite or catastrophic confinement-branch regressions instead of
  committing them merely because their Poisson residual passes. Rejected
  spikes no longer contaminate the per-mixing-level plateau detector.
- Structured-band and wide 3-D continuity fallbacks now equilibrate rows in
  `float128` before optimized LAPACK factorization and retry exact-zero pivots
  with a bounded roundoff-scale shift ladder. The original `float128`
  backward-residual gate remains authoritative; only rejected candidates use
  the portable banded/dense `float128` accuracy fallback.
  Failed Gummel polishes and max-iteration exits can no longer be accepted, and
  Newton explicitly rejects non-finite inputs, residuals, Jacobians, steps, and
  write-back states.
- Coupled Newton audits the true equilibrated linear residual and performs up
  to three mixed-precision refinement solves; an inaccurate external-solver
  status can no longer be mistaken for a usable nonlinear direction.
- A failed Gummel warm-up no longer lends its enlarged iteration budget to the
  much more expensive quad-precision Newton rescue. The rescue retains smaller
  caller limits and is capped at 60 coupled iterations before voltage
  continuation takes over.
- Potential and carrier boundary conditions now reject non-finite values,
  negative carrier densities, and node indices outside the grid. Zero density
  remains valid for insulating ferroelectric boundary nodes.

### Known limitations

- The updated 3/5/8/10 nm quantum-thickness family still requires completion
  of the common-path 8/10 nm replay and cross-thickness trend gates. The 3 nm
  ultrafine and 5 nm material-side cases pass individually; older 8 nm family
  artifacts must not be relabelled. The independently calibrated 8 nm baseline
  remains passed.
- Electrothermal replay uses a Sentaurus-calibrated ionization scale of 0.07 as
  a surrogate for the native high-field velocity-saturation model still to be
  implemented.
- IGZO and WSe2 device models are implemented but require experiment- or
  first-principles-constrained material files before quantitative calibration.
- IGZO/WSe2 release status is deliberately split by evidence level: IGZO has a
  Sentaurus-aligned full-DD tail selector for six accepted branches, while WSe2
  is released with Sentaurus response replay alignment only; WSe2
  compact/full-DD replacement remains diagnostic-only.

[0.2.0]: https://github.com/EDACraft/TCADCraft/tree/main
