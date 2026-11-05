# Validation scope for 0.3.0rc1

## Frozen numerical evidence

The candidate starts from 1,078 frozen development files. The input SHA-256
mapping is [frozen_source_identity.json](frozen_source_identity.json).
Release metadata/documentation/packaging edits are recorded separately; native
and Python solver implementations retain their frozen input identities.

[validation_summary.json](validation_summary.json) records sealed parent
manifest hashes and selected independent results. This compact provenance
summary does not replace the full raw numerical archives, which are not bundled.

| Evidence | Result | Limits |
| --- | --- | --- |
| Fine MoS₂ pulse, SI and legacy-charge | 2 complete 60 ps trajectories, 768 new steps, 8 full fields, 6,769,086 independent physics checks | 129×17×129 grid, 282,897 total/2,193 sheet nodes, prescribed 300 K model |
| Cross-profile comparison | Physical records exactly equal | Not arbitrary constants/physics preset validation |
| Phase endpoint reviews | All six 20/40/60 ps reviews passed | Overlaps full-pulse counts; not added again |
| Local-z probes | 4 steps, 8 fields, 1,336,524 independent field checks; exact profile parity | Initialization/one BE step at two refinements per profile; zero full pulses |
| Final-source affected regressions | 282 targeted cases passed in sealed development | Inherited; not a fresh full-suite result |

Pulse dt was 1.5625e-13 s, nonlinear tolerance 1e-12 and true row-scaled
linear max-norm limit 1e-14; thresholds were unchanged. Stage524 manifest:
`2695452c7a77b3fabbd93dc528cfd4db44f65b25f0b24117653b84050da261c9`.
Local-z manifest:
`465df9b967204877a0dca0bb6873fa184bdbe19d9fa3eae07f301daf3eb66ad8`.

## Open acceptance items

Overall physical/device qualification remains **false**. Original spatial
failures are retained. The reviewed 40 ps endpoint passed 11/14 four-level
spatial observables; sheet potential reduction ratio, dielectric potential
difference and electrostatic energy difference remained outside the original
gate. A complete trajectory and small residual do not establish mesh independence.

Still open: spatial qualification, fine-grid time/joint spacetime convergence,
real material/contact calibration, complete 2D logic/memory workflows,
dedicated quantum confinement/transport, and comprehensive commercial or
experimental acceptance. Local-z probe success does not close these items.
Real a/c relaxation calibration and independent measured electron/hole/lattice
temperatures remain separate research qualifications.

## Release build and installation verification

Release-specific results are recorded in [RELEASE_VERIFICATION.json](RELEASE_VERIFICATION.json):
**1055 passed, 0 skipped; zero failures/errors**, plus the README graphene example and MoS2 variant.
The wheel was built from the clean sdist and checked after a separate installation
outside the source tree. The full development suite was not rerun. Artifact checksums and a compatibility report identify the
actual binary. Historical counts above are not new packaging tests.

```bash
python scripts/release_check.py
```

Without external calibration arguments, this command checks release metadata
and source inventory only; it does not certify measured data or device convergence.
