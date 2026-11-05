"""Independent ledger coverage, clean controls, and atomic native rollback."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import numpy as np
import pytest
from test_three_temperature import case,BUDGET
from test_temperature_dependent_bands import band_case
from test_varshni_temperature_bands import configure
from tcad.postprocess.three_temperature_energy import audit_three_temperature_energy
from tcad.solver.device_three_temperature import DeviceThreeTemperature

COMMON=('energy_increments_J','outward_energy_J','integrated_particle_flux_s',
    'integrated_carrier_energy_flux_W','face_moments','cell_exchange_J','cell_electrical_work_J')
OPTIONAL=('cell_pair_generation_energy_J','cell_band_work_from_lattice_J',
    'cell_trap_capture_counts','cell_trap_carrier_energy_removed_J',
    'cell_radiative_carrier_energy_removed_J','cell_auger_carrier_energy_added_J')
TRAP_KEYS=('trap_capture_law','cell_trap_moments','cell_trap_particle_residuals',
    'cell_trap_capture_counts','cell_trap_carrier_energy_removed_J',
    'cell_trap_energy_increment_J','cell_trap_lattice_heat_J',
    'cell_trap_entropy_production_J_K','dynamic_trap_device_coupled')

@pytest.fixture(scope='module')
def complex_result():
    model,old=band_case(complex=True,count=2,contacts=True);configure(model)
    new,report=model.step(old,1e-15,**BUDGET)
    return model,old,new,report

@pytest.mark.parametrize('field',COMMON+OPTIONAL)
@pytest.mark.parametrize('damage',('extra_zero','extra_nonfinite','missing','nonmapping'))
def test_every_configured_energy_channel_must_be_covered(complex_result,field,damage):
    model,old,new,report=complex_result;bad=deepcopy(report)
    if damage=='extra_zero':bad[field]['unmodeled_reservoir']=0.
    elif damage=='extra_nonfinite':bad[field]['unmodeled_reservoir']=float('nan')
    elif damage=='missing':bad[field].pop('electrons')
    else:bad[field]=list(bad[field])
    with pytest.raises(ValueError,match='channel coverage mismatch'):
        audit_three_temperature_energy(model,old,new,bad,**BUDGET)

@pytest.fixture(scope='module')
def plain_result():
    model,old=case(count=1,uniform=True);new,report=model.step(old,2e-13,**BUDGET)
    return model,old,new,report

@pytest.mark.parametrize('field',TRAP_KEYS)
def test_unconfigured_trap_channel_is_rejected_even_when_zero(plain_result,field):
    model,old,new,report=plain_result;bad=deepcopy(report);bad[field]=0.
    with pytest.raises(ValueError,match='unconfigured trap report'):
        audit_three_temperature_energy(model,old,new,bad,**BUDGET)

@pytest.mark.parametrize('complex,contacts,nonlinear',[(False,False,False),(False,True,True),
    (True,False,False),(True,True,True)])
def test_clean_independent_reconstruction_is_exactly_equal_to_parent(complex,contacts,nonlinear):
    model,old=band_case(complex=complex,contacts=contacts,count=2 if contacts else 1)
    if nonlinear:configure(model)
    new,report=model.step(old,1e-15 if complex else 2e-13,**BUDGET)
    path=Path(__file__).resolve().parents[1]/'docs/validation/three_temperature_ledger_contract_20261021/before/tcad/postprocess/three_temperature_energy.py'
    spec=importlib.util.spec_from_file_location('tcad.postprocess._parent_ledger_contract',path)
    parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
    actual=audit_three_temperature_energy(model,old,new,report,**BUDGET)
    cell=actual.pop('independently_reconstructed_cell_ledger')
    assert actual==parent.audit_three_temperature_energy(model,old,new,report,**BUDGET)
    assert set(cell['energy_increments_J'])=={'electrons','holes','lattice'}|({'traps'} if model.trap_capture_law is not None else set())
    assert all(len(row)==model.nc for row in cell['energy_increments_J'].values())
    assert report['independent_audit']['valid']
    assert not report['complete_device_energy'] and not report['physical_validated']


def test_extra_storage_rejection_discards_prepared_native_state_and_allows_retry(monkeypatch):
    import tcad.postprocess.three_temperature_energy as module
    model,old=band_case(complex=True);device=DeviceThreeTemperature(model,old)
    accepted=device.state;saved=deepcopy(device.native_state())
    def corrupt(model,old,new,report,**budgets):
        report['energy_increments_J']['unmodeled_reservoir']=1.
        return audit_three_temperature_energy(model,old,new,report,**budgets)
    with monkeypatch.context() as patch:
        patch.setattr(module,'audit_three_temperature_energy',corrupt)
        with pytest.raises(ValueError,match='energy_increments_J channel coverage mismatch'):
            device.advance(1e-15,**BUDGET)
    assert device.state is accepted and device.native_state()==saved
    assert device._pending_token is None
    retry,_=device.advance(1e-15,**BUDGET)
    fresh,_=DeviceThreeTemperature(model,old).advance(1e-15,**BUDGET)
    for name in ('n_m3','p_m3','trap_fraction','temperature_K','electron_temperature_K','hole_temperature_K'):
        np.testing.assert_array_equal(getattr(retry,name),getattr(fresh,name))
