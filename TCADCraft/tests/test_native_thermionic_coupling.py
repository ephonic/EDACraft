import numpy as np

from tcad.physics.multivalley_thermionic import ThermionicValley
from tcad.solver.thermionic_electrothermal import ThermionicElectrothermalCutCellTransport
from test_thermionic_electrothermal import fixture


def test_solver_accepts_valley_resolved_interface_moments():
    model, state = fixture()
    model.thermionic_statistics = 'fermi_dirac'
    model.thermionic_valleys = {
        'electrons': (
            ThermionicValley('z', 2, .916, .190, .190),
            ThermionicValley('xy', 4, .190, .916, .190),
        )
    }
    poisson = model._poisson(state.n_m3, state.p_m3, state.trap_fraction, 1e-27)
    rows = model.interface_moments(state.n_m3, state.p_m3, state.temperature_K, poisson)
    assert rows['electrons']['moments']['statistics'] == 'fermi_dirac'
    assert rows['electrons']['moments']['valley_count'] == 2
    assert np.all(np.isfinite(rows['electrons']['moments']['material_energy_flux_W']))
    assert rows['holes']['moments']['particle_flux_s'].shape == model.ta.shape


def test_constructor_rejects_invalid_valley_statistics():
    model, _ = fixture()
    kwargs = dict(permittivity_F_m=1e-10, dirichlet_V=model.bc, mobility_n_m2_Vs=.01,
        mobility_p_m2_Vs=.01, thermionic_faces=model.tf.tolist(), thermionic_statistics='fd')
    try:
        ThermionicElectrothermalCutCellTransport(model.mesh, **kwargs)
    except ValueError:
        pass
    else:
        raise AssertionError('invalid statistics mode was accepted')
