"""Finite-range and strict-flag checks for Schottky injection currents."""
import math
import pytest

from tcad.physics.contact import SchottkyContactModel


def model(**kwargs):
    values = dict(barrier_height_eV=.8, effective_mass_ratio=.3)
    values.update(kwargs)
    return SchottkyContactModel(**values)


@pytest.mark.parametrize("temperature", [1e154, 1e308])
def test_unrepresentable_saturation_current_is_rejected(temperature):
    with pytest.raises(ValueError, match="saturation current.*representable"):
        model().saturation_current(temperature)


@pytest.mark.parametrize("include", ["true", 1, 0, None, 1.0])
def test_tunneling_switch_requires_explicit_boolean(include):
    with pytest.raises(ValueError, match="explicit boolean"):
        model().saturation_current(300., include)
    with pytest.raises(ValueError, match="explicit boolean"):
        model().current(.1, 300., include)


def test_finite_saturation_and_current_remain_unchanged_in_normal_range():
    contact = model(tunneling_barrier_lowering_eV=.1,
                    tunneling_cutoff_energy_eV=.8)
    saturation = contact.saturation_current(300.)
    current = contact.current(.1, 300.)
    enhanced = contact.current(.1, 300., True)
    assert math.isfinite(saturation) and saturation > 0.
    assert math.isfinite(current) and math.isfinite(enhanced)
    assert enhanced >= current


def test_representable_current_survives_unrepresentable_enhanced_saturation():
    contact = model(tunneling_barrier_lowering_eV=.2)
    # Is exceeds float64, but Is*expm1(V/nVT) remains finite at high T.
    result = contact.current(.1, 1e154, True)
    assert math.isfinite(result) and result > 0.


def test_components_report_finite_values():
    values = model(tunneling_barrier_lowering_eV=.05).components(.2, 300.)
    assert all(math.isfinite(value) for value in values.values())
