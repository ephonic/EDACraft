from test_electrothermal_cut_cell import fixture


def test_electrothermal_step_publishes_explicit_device_energy_schema():
    solver, state = fixture(open_contacts=True, quantum=True, traps=True)
    _, report = solver.step(state, 2e-12, charge_atol_C=2e-29,
                            particle_atol=1e-10, energy_atol_J=1e-28)
    assert report["device_energy_ledger_available"] is True
    assert report["device_energy_components"] == (
        "carrier", "trap", "thermal", "quantum", "electrostatic")
    assert set(report["energy_before_J"]) == set(report["energy_after_J"]) == set(report["energy_increments_J"])
    assert report["complete_device_energy"] is False
