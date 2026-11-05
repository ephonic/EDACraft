# Mechanism feature normalization

`attribute_mechanism` compares four feature magnitudes in the order drift,
diffusion, BTBT generation and FE polarization. These features support search
and inspection; their weights are **not conserved terminal-current fractions**.
Classical carrier currents can already include generated carriers, and the FE
characteristic magnitude is not a measured polarization derivative.

Existing calls retain `normalization="legacy_mixed"`: drift and diffusion use
A/m², integrated BTBT generation uses A, and polarization uses a historical
scale factor. Existing `MechanismReport` fields, positional construction and
four-element feature vectors are preserved. Search continues using this default.

To compare magnitudes in A/m², explicitly supply the physical cross-section
and, when polarization is nonzero, an FE characteristic time:

```python
from tcad.postprocess import attribute_mechanism

report = attribute_mechanism(
    simulator, result,
    normalization="current_density",
    cross_section_m2=width_m * thickness_m,
    fe_timescale_s=pulse_duration_s,
)
print(report.J_btbt, report.J_fe, report.component_unit)
print(report.feature_vector(), report.weights_available)
```

The cross-section must correspond to the full volume used for integrating
BTBT generation and the representative x cutline selected by `j` and `k`.
For a varying cross-section or nonuniform transverse transport, interpreting
one cutline as the whole device requires a separate physical justification.
The function does not infer area from padded one-dimensional mesh bounds.

The new `CurrentDensityMechanismReport` retains the original fields and adds
`J_btbt=I_btbt/cross_section_m2`, `J_fe=fe_charge/fe_timescale_s`, the supplied
scales, and `weights_available`. `normalization` reports `current_density` and
`component_unit` reports `A/m^2`. FE time may be omitted only for zero
polarization. Supplied scales must always be finite positive real scalars.
Nonfinite/negative generation and nonfinite feature magnitudes are rejected.
Finite components are normalized with a maximum scale to avoid sum overflow.
If all four magnitudes are zero, all weights are zero and
`weights_available=False`; the historical dominant-label fallback is `drift`.

This mode fixes dimensional comparability. It does not validate Kane material
parameters, FE dynamics, independent measurements or commercial device models.
Terminal-current conservation remains the responsibility of the terminal/KCL
and device energy audits.
