import pytest

from tcad.postprocess.device_energy import audit_complete_device_energy, solver_energy_history


def report():
    return {
        "energy_before_J": {"carrier_J": 2., "trap_J": 1., "thermal_J": 10., "quantum_J": .5, "electrostatic_J": 4.},
        "energy_after_J": {"carrier_J": 2.5, "trap_J": .8, "thermal_J": 10.2, "quantum_J": .6, "electrostatic_J": 4.1},
        "energy_increments_J": {"carrier_J": .5, "trap_J": -.2, "thermal_J": .2, "quantum_J": .1, "electrostatic_J": .1},
    }


def test_native_solver_report_enters_complete_five_component_ledger():
    history = solver_energy_history(report())
    audit = audit_complete_device_energy(history, components=("carrier", "trap", "thermal", "quantum", "electrostatic"))
    assert audit["valid"] and audit["storage_consistency_validated"]
    assert audit["complete_device_energy"] is False


def test_adapter_preserves_signed_exchange_and_rejects_missing_fields():
    history = solver_energy_history(report(), include_electrostatic=False)
    assert history[1]["interval_net_energy_J"]["trap"] == pytest.approx(-.2)
    bad = report()
    del bad["energy_increments_J"]["quantum_J"]
    with pytest.raises(ValueError): solver_energy_history(bad)
