"""Independent Decimal oracles for the complete thermionic exponential law."""
from decimal import Decimal, localcontext
import math

import pytest

from tcad.physics.contact import K_B_EV, RICHARDSON_M0, SchottkyContactModel


def reference(contact, voltage, temperature, include=False):
    """Evaluate physical factors without calling any contact implementation."""
    with localcontext() as ctx:
        ctx.prec = 800
        d = Decimal.from_float
        barrier = d(contact.barrier_height_eV)
        if include:
            lowering = contact.tunneling_barrier_lowering_eV
            if contact.tunneling_cutoff_energy_eV is not None:
                available = max(1. - max(voltage, 0.) /
                                contact.tunneling_cutoff_energy_eV, 0.)
                lowering *= available ** contact.tunneling_decay_exponent
            barrier = max(barrier - d(lowering), Decimal(0))
        thermal = d(K_B_EV) * d(temperature)
        prefactor = (d(RICHARDSON_M0) * d(contact.effective_mass_ratio)
                     * d(contact.richardson_multiplier) * d(contact.area_m2)
                     * d(temperature) ** 2)
        return float(prefactor * (-barrier / thermal).exp() *
                     ((d(voltage) / (thermal * d(contact.ideality_factor))).exp() - 1))


CASES = [
    dict(barrier_height_eV=b, area_m2=a)
    for b, a in [(.8, 1e-100), (2., 1e-30), (20., 1e-12)]
] + [
    dict(barrier_height_eV=.8, effective_mass_ratio=1e300,
         richardson_multiplier=1e100, area_m2=1e-300),
    dict(barrier_height_eV=.8, effective_mass_ratio=1e-300,
         richardson_multiplier=1e-100, area_m2=1e300),
]


@pytest.mark.parametrize("parameters", CASES)
@pytest.mark.parametrize("temperature", [200., 300., 600.])
@pytest.mark.parametrize("ideality", [1., 1.5])
def test_combined_exponential_matches_decimal(parameters, temperature, ideality):
    values = dict(effective_mass_ratio=.3, ideality_factor=ideality)
    values.update(parameters)
    contact = SchottkyContactModel(**values)
    voltage = 20. * ideality
    expected = reference(contact, voltage, temperature)
    if not math.isfinite(expected) or expected == 0.:
        with pytest.raises(ValueError, match="representable"):
            contact.current(voltage, temperature)
    else:
        assert contact.current(voltage, temperature) == pytest.approx(expected, rel=5e-13, abs=0.)


@pytest.mark.parametrize("voltage", [-100., -.1, .1, 100.])
@pytest.mark.parametrize("temperature", [1e154, 1e200])
def test_current_can_fit_when_saturation_does_not(voltage, temperature):
    contact = SchottkyContactModel(.8, .3)
    with pytest.raises(ValueError, match="saturation current.*representable"):
        contact.saturation_current(temperature)
    assert contact.current(voltage, temperature) == pytest.approx(
        reference(contact, voltage, temperature), rel=5e-13, abs=0.)


@pytest.mark.parametrize("voltage", [math.ulp(0.), -math.ulp(0.), 1e-300, -1e-300])
def test_underflowed_drive_does_not_erase_representable_current(voltage):
    contact = SchottkyContactModel(.8, .3)
    assert voltage / (K_B_EV * 1e300) == 0.
    assert contact.current(voltage, 1e300) == pytest.approx(
        reference(contact, voltage, 1e300), rel=5e-13, abs=0.)


@pytest.mark.parametrize("temperature", [200., 300., 600.])
@pytest.mark.parametrize("cutoff", [None, 30.])
@pytest.mark.parametrize("include", [False, True])
def test_tunneling_branch_uses_complete_exponential(temperature, cutoff, include):
    contact = SchottkyContactModel(20., .3, area_m2=1e-12,
        tunneling_barrier_lowering_eV=.1, tunneling_cutoff_energy_eV=cutoff)
    assert contact.current(20., temperature, include) == pytest.approx(
        reference(contact, 20., temperature, include), rel=5e-13, abs=0.)


@pytest.mark.parametrize("voltage", [-1., .1])
def test_unrepresentable_current_is_rejected_without_artificial_floor(voltage):
    contact = SchottkyContactModel(40., .3)
    assert reference(contact, voltage, 300.) == 0.
    with pytest.raises(ValueError, match="representable"):
        contact.current(voltage, 300.)
    with pytest.raises(ValueError, match="saturation current.*representable"):
        contact.saturation_current(300.)


@pytest.mark.parametrize("barrier", [0., 40., 1e308])
@pytest.mark.parametrize("resistance", [0., 1.])
def test_zero_bias_does_not_require_representable_saturation(barrier, resistance):
    contact = SchottkyContactModel(barrier, .3, series_resistance_ohm=resistance)
    assert contact.current(0., 300.) == 0.


@pytest.mark.parametrize("mass,multiplier,area", [
    (1e300, 1e100, 1e-300), (1e-300, 1e-100, 1e300),
])
def test_saturation_keeps_richardson_factors_separate(mass, multiplier, area):
    contact = SchottkyContactModel(.8, mass, richardson_multiplier=multiplier, area_m2=area)
    with localcontext() as ctx:
        ctx.prec = 800
        d = Decimal.from_float
        expected = float(d(RICHARDSON_M0) * d(mass) * d(multiplier) * d(area) *
                         Decimal(300) ** 2 * (-d(.8) / (d(K_B_EV) * 300)).exp())
    assert contact.saturation_current(300.) == pytest.approx(expected, rel=5e-13, abs=0.)


def test_series_branch_recovers_current_with_unrepresentable_saturation():
    contact = SchottkyContactModel(40., .3, series_resistance_ohm=1.)
    with pytest.raises(ValueError, match="saturation current.*representable"):
        contact.saturation_current(300.)
    got = contact.current(40., 300.)
    assert 0. < got < 40.
    assert reference(contact, 40. - got, 300.) == pytest.approx(got, rel=5e-12, abs=0.)


@pytest.mark.parametrize("voltage", [-1., -1e-20, 1e-20, .005])
@pytest.mark.parametrize("temperature", [200., 300., 600.])
def test_small_drive_and_reverse_current_match_decimal(voltage, temperature):
    contact = SchottkyContactModel(.8, .3, area_m2=1e-12)
    assert contact.current(voltage, temperature) == pytest.approx(
        reference(contact, voltage, temperature), rel=5e-13, abs=0.)


@pytest.mark.parametrize("voltage", [-.01, .01, .00001])
def test_representable_subnormal_output_is_not_rejected(voltage):
    contact = SchottkyContactModel(0., .3, area_m2=math.ulp(0.))
    expected = reference(contact, voltage, 300.)
    assert 0. < abs(expected) < 1e-308
    assert abs(contact.current(voltage, 300.) - expected) <= math.ulp(expected)


@pytest.mark.parametrize("cutoff", [None, 100.])
def test_enhanced_current_can_fit_when_unused_thermionic_branch_does_not(cutoff):
    contact = SchottkyContactModel(40., .3, area_m2=1e-12,
        tunneling_barrier_lowering_eV=39., tunneling_cutoff_energy_eV=cutoff)
    with pytest.raises(ValueError, match="representable"):
        contact.current(1., 300.)
    assert contact.current(1., 300., True) == pytest.approx(
        reference(contact, 1., 300., True), rel=5e-13, abs=0.)
