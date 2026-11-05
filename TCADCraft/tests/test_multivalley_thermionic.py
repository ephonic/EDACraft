import numpy as np
import pytest

from tcad.physics.multivalley_thermionic import ThermionicValley, multivalley_thermionic_interface_flux


VALLEYS = (
    ThermionicValley("Delta_z", 2, 0.916, 0.190, 0.190),
    ThermionicValley("Delta_xy", 4, 0.190, 0.916, 0.190, band_offset_neighbor_J=0.015 * 1.602176634e-19),
)


def call(n_owner, n_neighbor, statistics="fermi_dirac"):
    return multivalley_thermionic_interface_flux(
        n_owner, n_neighbor, 300., 330., 0.10 * 1.602176634e-19,
        0.12 * 1.602176634e-19, VALLEYS, 1e-14, potential_V=.02,
        statistics=statistics)


def test_unequal_valley_masses_and_degenerate_moments_are_finite():
    result = call(2e24, 8e23)
    assert result["statistics"] == "fermi_dirac"
    assert result["valley_count"] == 2
    assert result["forward_particle_rate_s"] > 0
    assert np.isfinite(result["material_energy_flux_W"])
    assert len(result["valley_moments"]) == 2


def test_equal_reservoir_detailed_balance_and_entropy():
    equal_valleys = (
        ThermionicValley("Delta_z", 2, 0.916, 0.190, 0.190),
        ThermionicValley("Delta_xy", 4, 0.190, 0.916, 0.190),
    )
    result = multivalley_thermionic_interface_flux(
        3e21, 3e21, 300., 300., .1 * 1.602176634e-19, .1 * 1.602176634e-19,
        equal_valleys, 1e-14)
    assert abs(result["particle_flux_s"]) < 1e-24
    assert abs(result["entropy_production_W_K"]) < 1e-24


def test_degenerate_supply_differs_from_boltzmann_at_high_density():
    fd = call(2e25, 8e23, "fermi_dirac")
    mb = call(2e25, 8e23, "boltzmann")
    assert abs(fd["forward_particle_rate_s"] - mb["forward_particle_rate_s"]) > 1e-4 * fd["forward_particle_rate_s"]


def test_low_density_fermi_limit_matches_boltzmann():
    fd = call(2e17, 8e16, "fermi_dirac")
    mb = call(2e17, 8e16, "boltzmann")
    assert fd["forward_particle_rate_s"] == pytest.approx(mb["forward_particle_rate_s"], rel=2e-3)
    assert fd["reverse_particle_rate_s"] == pytest.approx(mb["reverse_particle_rate_s"], rel=2e-3)


def test_invalid_statistics_and_duplicate_names_rejected():
    with pytest.raises(ValueError):
        call(1e20, 1e20, "kappa")
    with pytest.raises(ValueError):
        multivalley_thermionic_interface_flux(1e20, 1e20, 300., 300., 0., 0.,
            (ThermionicValley("x", 1, .2, .2, .2), ThermionicValley("x", 1, .3, .3, .3)), 1e-14)
