"""Prescribed affine band work in the stiff spatial FD excess formulation."""
from copy import deepcopy
from decimal import Decimal,localcontext
import numpy as np
import pytest
from tcad.solver.cut_cell_transport import Q,_immutable_state_array
from tcad.solver.lattice_excess import LatticeCoupledExcessRelaxation
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from tcad.postprocess.lattice_excess import audit_lattice_excess_step
from test_lattice_excess import lattice_case
from test_quad_lattice_excess import strong_case
from test_fermi_spectral import BUDGET


def affine_case(a=-20000.,c=20000.,count=2,graded=False,bath=False,strong=False,sign=1.):
    if strong:model,initial,power=strong_case(a,c,count,graded,bath)
    else:
        model,initial=lattice_case(a,c,count,graded)
        power=np.zeros((count,3))
    model.Ec=_immutable_state_array(np.full(count,.6*Q),float)
    model.Eh=_immutable_state_array(np.full(count,.4*Q),float)
    model.band_temperature_slopes=tuple(_immutable_state_array(np.linspace(s,1.2*s,count),float)
        for s in (sign*2e-23,sign*1e-23))
    return model,initial,power


@pytest.mark.parametrize('a,c',[(-20000.,20000.),(20000.,-20000.),(0.,0.)])
@pytest.mark.parametrize('sign',[-1.,1.])
@pytest.mark.parametrize('count,graded,bath,strong',[(2,False,False,False),(4,True,True,True)])
def test_stiff_affine_spatial_three_step_paths(a,c,sign,count,graded,bath,strong):
    model,initial,power=affine_case(a,c,count,graded,bath,strong,sign)
    d=LatticeCoupledExcessRelaxation(model,initial)
    for dt in (2e-14,5e-14,9e-14):
        old=d.state;new,r=d.advance(dt,source_power_W=power,**BUDGET)
        assert r['independent_audit']['valid']
        assert r['band_temperature_law']=='affine_lattice_temperature'
        assert not r['temperature_dependent_band_entropy_closed']
        assert any(Decimal(v)!=0 for row in r['cell_band_work_from_lattice_J'] for v in row)
        assert all(Decimal(cell.parameters[0])==1000 for cell in d.configuration.cells)
        assert not r['complete_device_energy'] and not r['physical_validated']
        assert d.native_state()==dict(state=new.raw(),time_s=new.time_s)
        with localcontext() as ctx:
            ctx.prec=90
            for i,cfg in enumerate(d.configuration.cells):
                delta=Decimal(new.cells[i].lattice_temperature_K)-Decimal(old.cells[i].lattice_temperature_K)
                expected=Decimal(cfg.parameters[0])+sum(Decimal(n)*Decimal(s) for n,s in
                    zip(cfg.initial_densities_m3,d.configuration.affine_bands[i][:2]))
                assert abs(Decimal(d.configuration.packed_parameters()[16*i])-expected)<Decimal('1e-28')
                assert Decimal(r['cell_lattice_energy_increments_J'][i])==Decimal(cfg.parameters[0])*Decimal(cfg.parameters[1])*delta
    # Maintained hot/cold baths can move Tl across Tref*(n/nref), so the sign
    # of a alone does not guarantee a small tau on those different paths.
    if a<0 and not bath:
        assert all(0<abs(Decimal(c.electron_excess_energy_J_m3))<Decimal('1e-60') for c in new.cells)


@pytest.mark.parametrize('sign',[-1.,1.])
def test_moderate_affine_solution_matches_general_native_equations(sign):
    model,initial,power=affine_case(-.4,.3,sign=sign)
    d=LatticeCoupledExcessRelaxation(model,initial);general=DeviceThreeTemperature(model,initial)
    for dt in (2e-14,5e-14):
        new,r=d.advance(dt,**BUDGET);other,g=general.advance(dt,**BUDGET)
        np.testing.assert_allclose([float(c.lattice_temperature_K) for c in new.cells],other.temperature_K,rtol=0,atol=2e-6)
        for k,label in enumerate(('electrons','holes')):
            np.testing.assert_allclose([float(v[k]) for v in r['cell_band_work_from_lattice_J']],
                g['cell_band_work_from_lattice_J'][label],rtol=2e-5,atol=1e-28)
            np.testing.assert_allclose([float(v[k]) for v in r['cell_exchange_J']],g['cell_exchange_J'][label],rtol=2e-5,atol=1e-27)


@pytest.mark.parametrize('damage',['sign','missing','lattice','carrier','law','entropy'])
def test_band_channel_audit_does_not_accept_cancelling_or_missing_work(damage):
    model,initial,power=affine_case();d=LatticeCoupledExcessRelaxation(model,initial);old=d.state
    new,r=d.advance(2e-14,**BUDGET);bad=deepcopy(r)
    if damage=='sign':bad['cell_band_work_from_lattice_J'][0][0]=str(-Decimal(bad['cell_band_work_from_lattice_J'][0][0]))
    elif damage=='missing':del bad['cell_band_work_from_lattice_J']
    elif damage=='lattice':bad['cell_lattice_energy_increments_J'][0]=str(Decimal(bad['cell_lattice_energy_increments_J'][0])+Decimal('1e-20'))
    elif damage=='carrier':bad['cell_carrier_energy_increments_J'][0][0]=str(Decimal(bad['cell_carrier_energy_increments_J'][0][0])+Decimal('1e-20'))
    elif damage=='law':bad['band_temperature_law']='microscopic_band_entropy'
    else:bad['temperature_dependent_band_entropy_closed']=True
    try:valid=audit_lattice_excess_step(d.configuration,old,new,bad,**BUDGET)['valid']
    except (ValueError,KeyError):valid=False
    assert not valid


@pytest.mark.parametrize('damage',['negative_capacity','zero_capacity','negative_gap','negative_varshni_alpha'])
def test_unsupported_band_domains_fail_before_native_initialization(damage):
    model,initial,power=affine_case()
    if damage.endswith('capacity'):
        model.band_temperature_slopes=tuple(np.full(2,(-6e-23 if damage=='negative_capacity' else -5e-23)) for _ in range(2))
    elif damage=='negative_gap':model.Ec=np.full(2,-1.)
    else:model.band_varshni_alpha=(np.full(2,-1e-25),np.zeros(2))
    with pytest.raises(ValueError):LatticeCoupledExcessRelaxation(model,initial)


def test_frozen_band_configuration_detaches_model_and_audit_failure_rolls_back(monkeypatch):
    import tcad.postprocess.lattice_excess as module
    model,initial,power=affine_case();d=LatticeCoupledExcessRelaxation(model,initial)
    expected=LatticeCoupledExcessRelaxation(model,initial);state,r=expected.advance(2e-14,**BUDGET)
    model.band_temperature_slopes=(np.zeros(2),np.zeros(2));before=d.native_state()
    with monkeypatch.context() as m:
        m.setattr(module,'audit_lattice_excess_step',lambda *a,**k:dict(valid=False))
        with pytest.raises(ValueError,match='audit'):d.advance(2e-14,**BUDGET)
    assert d.native_state()==before
    actual,report=d.advance(2e-14,**BUDGET)
    assert actual==state and report==r


def test_fixed_band_fingerprint_and_report_schema_are_unchanged():
    from tcad.solver.lattice_excess import LatticeExcessConfiguration
    model,initial=lattice_case();d=LatticeCoupledExcessRelaxation(model,initial);c=d.configuration
    assert c.sha256==LatticeExcessConfiguration(c.cells,c.faces,c.baths).sha256
    assert c.packed_parameters()==[v for cell in c.cells for v in cell.parameters]
    new,r=d.advance(2e-14,**BUDGET)
    assert 'cell_band_work_from_lattice_J' not in r
