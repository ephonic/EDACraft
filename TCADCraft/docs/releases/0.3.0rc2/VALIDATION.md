# Validation scope for 0.3.0rc2

The release incorporates numerical development through commit
`6f399e367db4a0848b7406768e203ee7daa143ce`. Solver/native sources are unchanged
from those studies, except the package version assignment. The freshly rebuilt
extension has its own binary hash; it is not identified as the reused study binary.
See [source identity](numerical_source_identity.json) and [summary](validation_summary.json).

## Inherited numerical evidence

| Control | Result | Remaining boundary |
| --- | --- | --- |
| [z/time matrix](../../optimization/20261108-geometric-z-time512/README.md) | z113/121/129, n128/256/512, x83/y9; 54/54 original gates at all dt | No combined x/y/z or absolute error bound |
| [Refined x/time](../../optimization/20261107-geometric-x83-time/README.md) | x69/75/83 at n128/256: 54/54 both | Coarser x65/69/75 remains 52/54 both |
| [y/time](../../optimization/20261107-geometric-y-time256/README.md) | Three y grids, two dt: 54/54 | Unresolved mixed increments do not establish decoupling |
| Latest fresh pulse subset | 2 full 60 ps pulses, 3072 steps, 8 fields, 2,089,230 physical/ledger checks | A subset of the nine-pulse matrix, never counted again |
| Trace analysis | 90 resolved decreasing time metrics across three z meshes | Conduction interval orders about 0.86; no uniform first-order/asymptotic claim |
| Solver / trace regressions | 245 / 25 passed in sealed development | Inherited here; not new packaging test counts |

Original nonlinear 1e-12 and true row-scaled linear max-norm 1e-14 gates,
fixed 65x9x65 observable support, scales, difference/ratio thresholds and floor
are unchanged. Failed coarse controls and memory/timeout evidence remain sealed.
All optimization report manifests are checked before release preparation.

## Fresh package verification

[RELEASE_VERIFICATION.json](RELEASE_VERIFICATION.json) and
[JUnit output](targeted_tests.xml) record this release's actual new build,
separate wheel installation and targeted tests. The wheel is built from a
clean sdist; installed module provenance is checked outside the source tree.
README graphene and MoS2 examples use the new geometric ordering. Tests cover
all sheet test modules plus native constants/precision contracts, including
the new ordering, cache-release and trace-analysis regressions. This is not
a full development-suite rerun. Calibration arguments are not supplied to the
metadata-only release check; no fresh calibration pass is implied.

## Open qualifications

Combined x/y/z controls and a physical observable tolerance budget are still
needed for joint spacetime qualification. Local node counts do not supply a
uniform global h ratio. Representative isothermal, homogeneous-band sheet
models do not qualify arbitrary 2D logic/memory, material/contact samples,
self-consistent Schrödinger–Poisson or NEGF transport.

Real nonzero a/c material calibration, independent electron/hole/lattice
temperature measurements, the complete 200 ps commercial/native three-temperature
profiles and general complex physics spacetime/energy/entropy closure remain
separate, previously excluded research items. No full Sentaurus equivalence,
new commercial run or experimental acceptance is claimed. Publication does not
replace the existing remote production installation.
