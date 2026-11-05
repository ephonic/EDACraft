from test_electrothermal_cut_cell import fixture

from tcad.postprocess.device_energy import audit_complete_device_energy, solver_energy_history, audit_solver_device_energy


def test_real_electrothermal_step_closes_through_native_adapter():
    solver, old = fixture(open_contacts=True, quantum=True, traps=True)
    new, report = solver.step(old, 2e-12, charge_atol_C=2e-29,
                              particle_atol=1e-10, energy_atol_J=1e-28)
    assert report["valid"] and report["temperature_feedback"]
    history = solver_energy_history(report)
    audit = audit_complete_device_energy(
        history,
        components=("carrier", "trap", "thermal", "quantum", "electrostatic"),
        rtol=2e-8,
        atol_J=1e-28,
    )
    assert audit["valid"] and audit["storage_consistency_validated"]
    assert audit["complete_device_energy"] is False
    independent = audit_solver_device_energy(solver, old, new, report,
        charge_atol_C=2e-29, particle_atol=1e-10, energy_atol_J=1e-28)
    assert independent['valid'] and independent['modeled_energy_balance_validated']
    assert audit["physical_validated"] is False
    assert new.time_s > old.time_s
