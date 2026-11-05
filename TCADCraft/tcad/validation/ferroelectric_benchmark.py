"""Native uniform-film replay for explicit commercial transient fixtures."""
import numpy as np

from tcad.core import PyDeviceSimulator


def run_uniform_film(case, data, *, nodes=9, select_steps=False):
    """Replay an explicit clock with cubic LK and zero carrier transport.

    The fixture supplies SI film geometry, epsilon, cubic coefficients and
    accepted times/voltages. Return actual states and unmodified port outputs.
    This uniform numerical fixture does not build a calibrated FeFET.
    """
    axis = case['axis']
    shape, spacing = [1, 1, 1], [1e-7, 1e-7, 1e-6]
    shape[axis], spacing[axis] = nodes, data['length_m']/(nodes-1)
    material = data['material']
    times, voltage = np.array(case['times_s']), np.array(case['top_voltage_V'])
    sim = PyDeviceSimulator(*shape, *spacing)
    sim.set_permittivity(np.full(nodes, data['epsilon_F_m']))
    sim.set_mobility(np.zeros(nodes), np.zeros(nodes))
    sim.set_doping(np.zeros(nodes))
    sim.set_effective_dos(np.full(nodes, 1e16), np.full(nodes, 1e16))
    sim.set_bandgap(np.full(nodes, 6.))
    sim.set_recombination(np.full(nodes, 1e100), np.full(nodes, 1e100))
    sim.set_dirichlet_potential({0: 0., nodes-1: 0.})
    sim.set_initial_guess(np.zeros(nodes), np.zeros(nodes), np.zeros(nodes))
    sim.set_ferroelectric_enabled(True)
    sim.set_ferroelectric_model(0)
    sim.set_ferroelectric_params(np.ones(nodes, dtype=np.int8), material['alpha_SI'], material['beta_SI'])
    sim.set_ferroelectric_gamma(material['viscosity_ohm_m'])
    sim.set_ferroelectric_polar_axis(axis)
    sim.set_transient_lk_coupled(True)
    if select_steps:
        sim.set_transient_lk_substepping(True, .5)
        sim.set_transient_lk_error_control(True, case['rtol'], case['atol'], 1e-16, 40)
    sim.set_transient_dt(float(times[-1]))
    sim.set_transient_t_final(float(times[-1]))
    sim.set_transient_voltage_waveforms(times, {nodes-1: voltage})
    sim.set_gummel_max_iter(80)
    sim.set_tolerance(1e-12)
    history = sim.solve_transient()
    if not all(s['valid'] and s['converged'] for s in history):
        raise ValueError('uniform-film replay did not converge')
    if not select_steps:
        np.testing.assert_array_equal([s['time_s'] for s in history], times)
    return history, dict(
        polarization_C_m2=np.array([s['P'].reshape(-1, 3)[:, axis].mean() for s in history]),
        top_charge_C=np.array([s['electrode_charges_C'][1] for s in history]),
        top_current_A=np.r_[0., [s['electrode_total_currents_A'][1] for s in history[1:]]])
