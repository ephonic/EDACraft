import pytest

from tcad.postprocess.device_energy import audit_complete_device_energy


def history():
    return [
        {"energy_storage_J": {"carrier": 2.0, "trap": 1.0, "thermal": 10.0, "quantum": .5}},
        {"energy_storage_J": {"carrier": 3.0, "trap": 0.5, "thermal": 10.2, "quantum": .6},
         "interval_net_energy_J": {"carrier": 1.0, "trap": -.5, "thermal": .2, "quantum": .1}},
    ]


def test_complete_component_ledger_closes_and_reports_scope():
    report = audit_complete_device_energy(history())
    assert report["valid"] and report["storage_consistency_validated"]
    assert report["energy_balance_validated"] is False
    assert report["complete_device_energy"] is False
    assert report["max_component_residual_J"] == pytest.approx(0.)
    assert report["physical_validated"] is False


def test_carrier_trap_exchange_is_retained_in_total_closure():
    report = audit_complete_device_energy(history())
    row = report["interval_residuals_J"][0]
    assert row["carrier"] == pytest.approx(0.) and row["trap"] == pytest.approx(0.)
    assert row["total"] == pytest.approx(0.)


def test_missing_or_corrupt_component_cannot_be_treated_as_zero():
    broken = history()
    del broken[1]["interval_net_energy_J"]["quantum"]
    with pytest.raises(ValueError):
        audit_complete_device_energy(broken)
    broken = history()
    broken[1]["interval_net_energy_J"]["thermal"] += .2
    assert not audit_complete_device_energy(broken)["valid"]


def test_invalid_snapshot_contract_is_rejected():
    with pytest.raises(ValueError): audit_complete_device_energy([history()[0]])
    with pytest.raises(ValueError): audit_complete_device_energy(history(), rtol=1.)
