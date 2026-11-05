"""Exact prescribed nonlinear band work under the original stiff excess laws."""
from copy import deepcopy
from decimal import Decimal,localcontext
import numpy as np
import pytest
from test_affine_band_excess import affine_case,BUDGET
from tcad.solver.lattice_excess import LatticeCoupledExcessRelaxation
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from tcad.postprocess.lattice_excess import audit_lattice_excess_step


def varshni_case(a=-20000.,c=20000.,count=2,graded=False,bath=False,strong=False,sign=1.,beta=300.):
    model,initial,power=affine_case(a,c,count,graded,bath,strong,sign)
    model.band_varshni_alpha=(np.linspace(1e-23,1.2e-23,count),np.linspace(.5e-23,.6e-23,count))
    model.band_varshni_beta=(np.full(count,beta),np.full(count,beta*1.5))
    return model,initial,power


@pytest.mark.parametrize('a,c',[(-20000.,20000.),(20000.,-20000.),(0.,0.)])
@pytest.mark.parametrize('sign',[-1.,1.])
@pytest.mark.parametrize('count,graded,bath,strong',[(2,False,False,False),(4,True,True,True)])
def test_stiff_nonlinear_three_step_paths(a,c,sign,count,graded,bath,strong):
    model,initial,power=varshni_case(a,c,count,graded,bath,strong,sign)
    d=LatticeCoupledExcessRelaxation(model,initial)
    for dt in (2e-14,5e-14,9e-14):
        old=d.state;new,r=d.advance(dt,source_power_W=power,**BUDGET)
        assert r['independent_audit']['valid']
        assert r['band_temperature_law']=='affine_plus_Varshni_lattice_temperature'
        assert r['nonlinear_band_storage_primitive']=='exact_Varshni_divided_difference'
        assert not r['temperature_dependent_band_entropy_closed']
        assert not r['complete_device_energy'] and not r['physical_validated']
        assert d.native_state()==dict(state=new.raw(),time_s=new.time_s)
        with localcontext() as ctx:
            ctx.prec=90
            for i,cfg in enumerate(d.configuration.cells):
                T=Decimal(new.cells[i].lattice_temperature_K);oldT=Decimal(old.cells[i].lattice_temperature_K)
                for k in range(2):
                    slope=Decimal(d.configuration.affine_bands[i][k])
                    alpha,beta=map(Decimal,d.configuration.varshni_bands[i][2*k:2*k+2])
                    # Direct independent primitive subtraction is safe in this
                    # moderate-beta fixture; it checks the secant implementation.
                    work=Decimal(cfg.parameters[1])*Decimal(cfg.initial_densities_m3[k])*(
                        slope*(T-oldT)-alpha*(T*T/(T+beta)-oldT*oldT/(oldT+beta)))
                    assert abs(Decimal(r['cell_band_work_from_lattice_J'][i][k])-work)<Decimal('1e-45')
    if a<0 and not bath:
        assert all(0<abs(Decimal(c.electron_excess_energy_J_m3))<Decimal('1e-60') for c in new.cells)


@pytest.mark.parametrize('sign',[-1.,1.])
def test_moderate_solution_matches_general_varshni_native_rows(sign):
    model,initial,power=varshni_case(-.4,.3,sign=sign)
    d=LatticeCoupledExcessRelaxation(model,initial);g=DeviceThreeTemperature(model,initial)
    for dt in (2e-14,5e-14):
        new,r=d.advance(dt,**BUDGET);other,gr=g.advance(dt,**BUDGET)
        np.testing.assert_allclose([float(c.lattice_temperature_K) for c in new.cells],other.temperature_K,atol=2e-6,rtol=0)
        for k,name in enumerate(('electrons','holes')):
            np.testing.assert_allclose([float(v[k]) for v in r['cell_band_work_from_lattice_J']],
                gr['cell_band_work_from_lattice_J'][name],rtol=2e-5,atol=1e-28)
            np.testing.assert_allclose([float(v[k]) for v in r['cell_exchange_J']],
                gr['cell_exchange_J'][name],rtol=2e-5,atol=1e-27)


def test_zero_beta_matches_equivalent_affine_physics():
    model,initial,power=varshni_case(-.4,.3,beta=0.)
    affine=deepcopy(model)
    affine.band_temperature_slopes=tuple(s-a for s,a in zip(model.band_temperature_slopes,model.band_varshni_alpha))
    affine.band_varshni_alpha=(np.zeros(2),np.zeros(2))
    nonlinear=LatticeCoupledExcessRelaxation(model,initial);linear=LatticeCoupledExcessRelaxation(affine,initial)
    a,ra=nonlinear.advance(2e-14,**BUDGET);b,rb=linear.advance(2e-14,**BUDGET)
    np.testing.assert_allclose([float(s.lattice_temperature_K) for s in a.cells],
        [float(s.lattice_temperature_K) for s in b.cells],rtol=0,atol=1e-10)
    np.testing.assert_allclose(np.array(ra['cell_band_work_from_lattice_J'],float),
        np.array(rb['cell_band_work_from_lattice_J'],float),rtol=1e-9,atol=1e-29)


def test_huge_beta_keeps_tiny_curvature_finite():
    model,initial,power=varshni_case(beta=1e300)
    d=LatticeCoupledExcessRelaxation(model,initial);new,r=d.advance(2e-14,**BUDGET)
    assert r['independent_audit']['valid']
    assert all(Decimal(v).is_finite() for row in r['cell_band_work_from_lattice_J'] for v in row)


@pytest.mark.parametrize('damage',['tangent','missing','law','entropy','carrier','lattice'])
def test_audit_rejects_false_nonlinear_channels(damage):
    model,initial,power=varshni_case();d=LatticeCoupledExcessRelaxation(model,initial);old=d.state
    new,r=d.advance(2e-14,**BUDGET);bad=deepcopy(r)
    if damage=='tangent':
        with localcontext() as ctx:
            ctx.prec=90
            i=k=0;cfg=d.configuration.cells[i];T=Decimal(new.cells[i].lattice_temperature_K)
            oldT=Decimal(old.cells[i].lattice_temperature_K);alpha,beta=map(Decimal,d.configuration.varshni_bands[i][:2])
            endpoint_work=Decimal(cfg.parameters[1])*Decimal(cfg.initial_densities_m3[k])*(T-oldT)*(
                Decimal(d.configuration.affine_bands[i][k])-alpha*T*(T+2*beta)/(T+beta)**2)
            assert abs(endpoint_work-Decimal(bad['cell_band_work_from_lattice_J'][i][k]))>Decimal('1e-27')
            bad['cell_band_work_from_lattice_J'][i][k]=str(endpoint_work)
    elif damage=='missing':del bad['nonlinear_band_storage_primitive']
    elif damage=='law':bad['band_temperature_law']='affine_lattice_temperature'
    elif damage=='entropy':bad['temperature_dependent_band_entropy_closed']=True
    elif damage=='carrier':bad['cell_carrier_energy_increments_J'][0][0]='1e-15'
    else:bad['cell_lattice_energy_increments_J'][0]='1e-15'
    try:valid=audit_lattice_excess_step(d.configuration,old,new,bad,**BUDGET)['valid']
    except (ValueError,KeyError):valid=False
    assert not valid


@pytest.mark.parametrize('damage',['negative_alpha','negative_beta','capacity','gap'])
def test_uncertified_domains_rejected(damage):
    model,initial,power=varshni_case()
    if damage=='negative_alpha':model.band_varshni_alpha=(np.full(2,-1e-23),np.zeros(2))
    elif damage=='negative_beta':model.band_varshni_beta=(np.full(2,-1.),np.zeros(2))
    elif damage=='capacity':model.band_varshni_alpha=(np.full(2,1e-20),np.zeros(2))
    else:model.band_varshni_alpha=(np.full(2,2e-21),np.full(2,2e-21));model.capacity=np.full(2,1e5)
    with pytest.raises(ValueError):LatticeCoupledExcessRelaxation(model,initial)


@pytest.mark.parametrize('exception',[ValueError,KeyboardInterrupt])
def test_audit_exception_rolls_back_and_configuration_is_frozen(monkeypatch,exception):
    import tcad.postprocess.lattice_excess as audit
    model,initial,power=varshni_case();d=LatticeCoupledExcessRelaxation(model,initial)
    expected=LatticeCoupledExcessRelaxation(model,initial);new,r=expected.advance(2e-14,**BUDGET)
    model.band_varshni_alpha[0][:]=0
    before=d.native_state()
    def fail(*a,**k):raise exception('rejected')
    with monkeypatch.context() as m:
        m.setattr(audit,'audit_lattice_excess_step',fail)
        with pytest.raises(exception):d.advance(2e-14,**BUDGET)
    assert d.native_state()==before
    actual,report=d.advance(2e-14,**BUDGET)
    assert actual==new and report==r
