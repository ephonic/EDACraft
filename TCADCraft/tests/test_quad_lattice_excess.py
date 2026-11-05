"""Precision stress controls; conductivities are numerical controls, not materials."""
from copy import deepcopy
from decimal import Decimal,localcontext
import numpy as np
import pytest
from test_lattice_excess import lattice_case,BUDGET
from test_thermal_bath_excess import bath_case
from tcad.solver.lattice_excess import LatticeCoupledExcessRelaxation
from tcad.postprocess.lattice_excess import audit_lattice_excess_step


def strong_case(a=-20000.,c=20000.,count=2,graded=False,bath=False,kappa=1e12):
    model,initial=lattice_case(a,c,count,graded,kappa=kappa)
    if bath:
        other,_=bath_case(a,c,count,graded);model.bath=other.bath
    power=np.array([[1e-5 if i%2==0 else 0.,-1e-5 if i%2 else 0.,(i-(count-1)/2)*1e-5] for i in range(count)])
    return model,initial,power


@pytest.mark.parametrize('a,c',[(-20000.,20000.),(20000.,-20000.),(0.,0.)])
@pytest.mark.parametrize('count,graded',[(2,False),(4,True)])
@pytest.mark.parametrize('bath',[False,True])
def test_strong_conduction_three_steps_close_with_same_physical_budgets(a,c,count,graded,bath):
    model,initial,power=strong_case(a,c,count,graded,bath);d=LatticeCoupledExcessRelaxation(model,initial);retried=False
    for h in (2e-14,5e-14,9e-14):
        old=d.state;new,r=d.advance(h,source_power_W=power,**BUDGET)
        retried|=r.get('lattice_coordinate_precision')=='float128'
        assert r['residual_evaluations']<=600
        audit=audit_lattice_excess_step(d.configuration,old,new,r,source_power_W=power,**BUDGET)
        assert audit['valid'] and not audit['native_operators_used']
        assert d.native_state()==dict(state=new.raw(),time_s=new.time_s)
        assert not r['complete_device_energy'] and not r['general_carrier_transport_integrated']
    assert retried


def test_rounding_accepted_temperature_coordinates_to_float64_violates_face_budget():
    model,initial,power=strong_case();d=LatticeCoupledExcessRelaxation(model,initial)
    new,r=d.advance(2e-14,source_power_W=power,**BUDGET)
    assert r['lattice_coordinate_precision']=='float128'
    with localcontext() as ctx:
        ctx.prec=90
        a,b,A,do,dn,ko,kn=d.configuration.faces[0]
        rounded=Decimal.from_float(r['dt_s'])*Decimal(A)/(Decimal(do)/Decimal(ko)+Decimal(dn)/Decimal(kn))*\
            (Decimal.from_float(float(new.cells[a].lattice_temperature_K))-Decimal.from_float(float(new.cells[b].lattice_temperature_K)))
        assert abs(rounded-Decimal(r['face_energy_impulses_J'][0]))>Decimal('1e-27')


def test_failed_float64_work_and_quad_retry_share_one_evaluation_budget():
    model,initial,power=strong_case();d=LatticeCoupledExcessRelaxation(model,initial)
    expected,report=d.advance(2e-14,source_power_W=power,**BUDGET);n=report['residual_evaluations']
    limited=LatticeCoupledExcessRelaxation(model,initial);before=limited.native_state()
    with pytest.raises(RuntimeError,match='budget'):
        limited.advance(2e-14,source_power_W=power,max_nfev=n-1,**BUDGET)
    assert limited.native_state()==before
    actual,retry=limited.advance(2e-14,source_power_W=power,max_nfev=n,**BUDGET)
    assert actual==expected and retry==report


@pytest.mark.parametrize('damage',['precision','reason','counter_scope','partial'])
def test_independent_audit_rejects_precision_metadata_tampering(damage):
    model,initial,power=strong_case();d=LatticeCoupledExcessRelaxation(model,initial);old=d.state
    new,r=d.advance(2e-14,source_power_W=power,**BUDGET);bad=deepcopy(r)
    if damage=='precision':bad['lattice_coordinate_precision']='float64'
    elif damage=='reason':bad['precision_fallback_reason']='reset_budget'
    elif damage=='counter_scope':bad['iteration_counter_scope']='all_attempts'
    else:del bad['precision_fallback_reason']
    with pytest.raises(ValueError,match='precision'):
        audit_lattice_excess_step(d.configuration,old,new,bad,source_power_W=power,**BUDGET)


@pytest.mark.parametrize('failure',['audit','interrupt'])
def test_quad_candidate_does_not_commit_when_audit_fails(monkeypatch,failure):
    import tcad.postprocess.lattice_excess as module
    model,initial,power=strong_case();d=LatticeCoupledExcessRelaxation(model,initial);before=d.native_state()
    expected=LatticeCoupledExcessRelaxation(model,initial);state,report=expected.advance(2e-14,source_power_W=power,**BUDGET)
    def deny(*args,**kwargs):
        if failure=='interrupt':raise KeyboardInterrupt()
        return {'valid':False}
    with monkeypatch.context() as patch:
        patch.setattr(module,'audit_lattice_excess_step',deny)
        with pytest.raises((ValueError,KeyboardInterrupt)):d.advance(2e-14,source_power_W=power,**BUDGET)
    assert d.native_state()==before
    actual,retry=d.advance(2e-14,source_power_W=power,**BUDGET)
    assert actual==state and retry==report
