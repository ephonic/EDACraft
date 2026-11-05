"""Dense biased FD steps retain real density bits and independent closure."""
from copy import deepcopy
import numpy as np
import pytest
from test_fermi_spectral import fixture,BUDGET
from tcad.solver.fermi_electrothermal import FermiSpectralState
from tcad.solver.cut_cell_transport import CutCellState
from tcad.postprocess.fermi_spectral_energy import audit_fermi_spectral_energy


@pytest.mark.parametrize('voltage',[.002,-.002])
@pytest.mark.parametrize('count',[2,4])
def test_dense_biased_three_continued_steps_have_independent_energy_and_charge_closure(voltage,count):
    model,state=fixture(contacts=True,voltage=voltage,count=count,density_scale=10.)
    for _ in range(3):
        old=state;state,report=model.step(old,2e-13,**BUDGET)
        audit=audit_fermi_spectral_energy(model,old,state,report,**BUDGET)
        assert audit['valid'],audit
        assert isinstance(state,FermiSpectralState) and isinstance(state,CutCellState)
        assert report['density_precision']['mantissa_bits']==np.finfo(np.longdouble).nmant+1
        assert report['density_precision']['mantissa_bits']>53
        assert abs(audit['charge_balance_residual_C'])<=BUDGET['charge_atol_C']
        for value in (state.n_m3,state.p_m3,state.temperature_K,state.trap_fraction):
            assert not value.flags.writeable


@pytest.mark.parametrize('voltage',[.002,-.002])
def test_dense_biased_time_refinement(voltage):
    endpoints=[]
    for count in (1,2,4):
        model,state=fixture(contacts=True,voltage=voltage,density_scale=10.)
        for _ in range(count):
            old=state;state,report=model.step(old,2e-13/count,**BUDGET)
            assert audit_fermi_spectral_energy(model,old,state,report,**BUDGET)['valid']
        endpoints.append(np.r_[state.n_m3/1e26,state.temperature_K/350.])
    errors=[np.linalg.norm(a-endpoints[-1]) for a in endpoints[:-1]]
    assert errors[1]<errors[0]


def test_extended_state_survives_binary_roundtrip_and_copies_input_arrays(tmp_path):
    model,old=fixture(contacts=True,voltage=.002,density_scale=10.)
    new,report=model.step(old,2e-13,**BUDGET)
    path=tmp_path/'state.npz'
    np.savez(path,n=new.n_m3,p=new.p_m3,T=new.temperature_K,f=new.trap_fraction,time=new.time_s)
    with np.load(path) as values:
        n=values['n'];restored=FermiSpectralState(n,values['p'],values['f'],values['T'],float(values['time']))
    np.testing.assert_array_equal(new.n_m3,restored.n_m3)
    n[:]=1.
    assert audit_fermi_spectral_energy(model,old,restored,report,**BUDGET)['valid']
    assert not restored.n_m3.flags.writeable


@pytest.mark.parametrize('damage',['precision','charge','work_split'])
def test_independent_audit_checks_precision_charge_and_work_split(damage):
    model,old=fixture(contacts=True,voltage=.002,density_scale=10.)
    new,report=model.step(old,2e-13,**BUDGET);bad=deepcopy(report)
    if damage=='precision':bad['density_precision']['mantissa_bits']=53
    elif damage=='charge':bad['charge_balance_residual_C']+=1e-25
    else:
        bad['displacement_work_J']+=1e-24;bad['conduction_work_J']-=1e-24
    assert not audit_fermi_spectral_energy(model,old,new,bad,**BUDGET)['valid']


def test_state_copy_keeps_sub_float64_density_difference():
    large=np.longdouble('1e26');small=large+np.longdouble('1e9')
    assert float(small)==float(large)
    state=FermiSpectralState([large],[small],[.3],[300.])
    assert state.p_m3[0]>state.n_m3[0]
    assert CutCellState([large],[small],[.3],[300.]).p_m3[0]==float(large)
