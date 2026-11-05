"""Dimensional feature controls; controlled fields are not commercial acceptance."""
from dataclasses import asdict
import itertools
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from tcad.core import native_constants
from tcad.mesh.structured_grid import StructuredGrid
from tcad.postprocess import CurrentDensityMechanismReport
from tcad.postprocess.mechanism import attribute_mechanism, MechanismReport, MECHANISM_LABELS
from tcad.postprocess.current import contact_current_1d
from test_current_charge_consistency import problem


CASES=list(itertools.product(['line','slab_x'],range(3),[1.,7.],[1e-4,1e-10]))


def controlled(geometry='line', axis=0, scale=1.):
    x=np.array([0.,.06,.24,.42,.6])*1e-6
    z=np.array([0.,.05,.2,.4])*1e-6 if geometry=='slab_x' else np.array([0.])
    thickness=2e-7*scale; depth=.4e-6 if geometry=='slab_x' else 1e-6
    mesh=StructuredGrid(((0.,.6e-6),(0.,thickness),(0.,depth)),len(x),1,len(z),axes=[x,np.array([0.]),z])
    mesh.fields.update(mu_n=np.full(mesh.npts(),.1),mu_p=np.full(mesh.npts(),.05))
    xx=mesh.flat_coords()[0]; size=mesh.npts()
    q={'si':1.602176634e-19,'legacy-charge':1.602192e-19}[native_constants()['profile']]
    sim=SimpleNamespace(mesh=mesh,VT=.02585,elementary_charge_C=q)
    P=np.zeros((size,3));P[:,axis]=.01
    state=dict(phi=xx*1e4,n=1e20+1e26*xx,p=2e20+2e25*xx,P=P,G_btbt=np.full(size,1e30))
    return sim,state,thickness*depth


def density_report(sim,state,area,time=None):
    return attribute_mechanism(sim,state,normalization='current_density',cross_section_m2=area,fe_timescale_s=time)


def record(geometry,axis,scale,time):
    sim,state,area=controlled(geometry,axis,scale)
    report=density_report(sim,state,area,time)
    return dict(geometry=geometry,axis=axis,scale=scale,time_s=time,area_m2=area,
                charge_C=sim.elementary_charge_C,VT=sim.VT,volume_m3=float(sim.mesh.control_volumes().sum()),
                components_A_m2=[report.J_drift,report.J_diff,report.J_btbt,report.J_fe],
                I_btbt_A=report.I_btbt,fe_charge_C_m2=report.fe_charge,
                weights=report.feature_vector().tolist(),dominant=report.dominant,
                available=report.weights_available,unit=report.component_unit,normalization=report.normalization)


@pytest.mark.parametrize('geometry,axis,scale,time',CASES)
def test_density_components_have_explicit_units_and_analytic_weights(geometry,axis,scale,time):
    row=record(geometry,axis,scale,time)
    # Independent affine edge averages; no runtime split/reference helper.
    midpoint_mean=np.mean([.03,.15,.33,.51])*1e-6
    q=row['charge_C']
    expected=np.array([q*(.1*(1e20+1e26*midpoint_mean)+.05*(2e20+2e25*midpoint_mean))*1e4,
                       q*.02585*(.1*1e26-.05*2e25),q*1e30*.6e-6,.01/time])
    np.testing.assert_allclose(row['components_A_m2'],expected,rtol=3e-14,atol=0.)
    np.testing.assert_allclose(row['weights'],expected/expected.sum(),rtol=3e-14,atol=0.)
    assert row['I_btbt_A']==pytest.approx(expected[2]*row['area_m2'],rel=3e-14)
    assert row['volume_m3']==pytest.approx(.6e-6*row['area_m2'],rel=3e-14)
    assert row['dominant']==MECHANISM_LABELS[int(np.argmax(expected))]
    assert row['available'] and row['unit']=='A/m^2' and row['normalization']=='current_density'


@pytest.mark.parametrize('geometry',['line','slab_x'])
def test_transverse_area_scaling_preserves_density_weights(geometry):
    a=record(geometry,0,1.,1e-4); b=record(geometry,0,7.,1e-4)
    assert b['I_btbt_A']/a['I_btbt_A']==pytest.approx(7.,rel=3e-14)
    np.testing.assert_allclose(a['components_A_m2'],b['components_A_m2'],rtol=3e-14,atol=0.)
    np.testing.assert_allclose(a['weights'],b['weights'],rtol=3e-14,atol=0.)


@pytest.mark.parametrize('time',[None,1e-9,np.float64(1e-8)])
def test_zero_signal_has_unavailable_zero_weights_and_optional_time(time):
    sim,state,area=controlled()
    for v in state.values():v.fill(0.)
    report=density_report(sim,state,area,time)
    assert not report.weights_available and report.J_fe==report.J_btbt==0.
    assert report.fe_timescale_s==time
    np.testing.assert_array_equal(report.feature_vector(),np.zeros(4))


@pytest.mark.parametrize('name',['cross_section_m2','fe_timescale_s'])
@pytest.mark.parametrize('value',[0.,-1.,np.nan,np.inf,-np.inf,True,[1e-12],[[1e-12]],'1e-12',1e-12+0j])
def test_invalid_scales_rejected_without_mutation(name,value):
    sim,state,area=controlled(); before={k:v.copy() for k,v in state.items()}
    options=dict(normalization='current_density',cross_section_m2=area,fe_timescale_s=1e-9);options[name]=value
    with pytest.raises(ValueError,match=name):attribute_mechanism(sim,state,**options)
    for k,v in state.items():np.testing.assert_array_equal(v,before[k])


def test_explicit_area_and_nonzero_fe_time_are_required():
    sim,state,area=controlled()
    with pytest.raises(ValueError,match='cross_section_m2'):attribute_mechanism(sim,state,normalization='current_density')
    with pytest.raises(ValueError,match='fe_timescale_s'):density_report(sim,state,area)
    state.pop('P')
    assert density_report(sim,state,area).J_fe==0.


@pytest.mark.parametrize('options',[dict(normalization='unknown'),dict(normalization=None),dict(normalization=['current_density']),dict(cross_section_m2=1e-12),dict(fe_timescale_s=1e-9)])
def test_mode_and_unused_scale_rejection(options):
    sim,state,_=controlled()
    with pytest.raises(ValueError):attribute_mechanism(sim,state,**options)


@pytest.mark.parametrize('field,value',[('G_btbt',-1.),('G_btbt',np.nan),('G_btbt',np.inf),('P',np.nan),('P',np.inf),('n',np.nan)])
def test_nonfinite_or_negative_components_are_rejected(field,value):
    sim,state,area=controlled();state[field].fill(value)
    with pytest.raises(ValueError,match='finite'):density_report(sim,state,area,1e-9)


def test_extreme_finite_components_normalize_without_sum_overflow():
    sim,state,area=controlled()
    state['phi'].fill(0.);state['n'].fill(0.);state['p'].fill(0.)
    report=density_report(sim,state,2e-316,1e-310)
    assert np.isfinite(report.J_btbt) and np.isfinite(report.J_fe)
    assert report.J_btbt+report.J_fe==np.inf  # naive sum would discard finite signals
    assert report.weights_available and report.feature_vector().sum()==pytest.approx(1.,rel=2e-15)
    expected=report.J_fe/report.J_btbt
    assert report.fractions['fe_polarization']/report.fractions['btbt']==pytest.approx(expected,rel=3e-14)


@pytest.mark.parametrize('name',['area','time'])
def test_scale_conversion_overflow_is_rejected(name):
    sim,state,area=controlled()
    with pytest.raises(ValueError,match='component magnitudes'):
        density_report(sim,state,5e-324 if name=='area' else area,5e-324 if name=='time' else 1e-9)


def test_report_and_search_feature_compatibility():
    from tcad.search.evolution import Candidate
    from tcad.search.grammar import tree_from_template
    sim,state,area=controlled()
    legacy=attribute_mechanism(sim,state); explicit=attribute_mechanism(sim,state,normalization='legacy_mixed')
    assert type(legacy) is MechanismReport and legacy.normalization=='legacy_mixed' and legacy.component_unit=='mixed'
    assert set(asdict(legacy))=={'dominant','fractions','J_drift','J_diff','I_btbt','fe_charge','cutline_x'}
    np.testing.assert_array_equal(legacy.feature_vector(),explicit.feature_vector())
    positional=MechanismReport('drift',dict(zip(MECHANISM_LABELS,[1.,0.,0.,0.])),1.,0.,0.,0.)
    np.testing.assert_array_equal(positional.feature_vector(),[1.,0.,0.,0.])
    normalized=density_report(sim,state,area,1e-9)
    assert isinstance(normalized,CurrentDensityMechanismReport) and isinstance(normalized,MechanismReport)
    cand=Candidate(tree=tree_from_template('mosfet'),template_name='mosfet')
    for report in [legacy,normalized]:
        cand.mechanism=report
        assert cand.feature_vector().shape==(22,)
        np.testing.assert_array_equal(cand.feature_vector()[-4:],report.feature_vector())


@pytest.mark.parametrize('bias',[.01,-.01])
def test_native_neutral_resistor_density_is_unchanged(bias):
    sim,x,_=problem('line');low=sim._sim;size=sim.mesh.npts();density=1e16
    low.set_mobility(sim.mesh.fields['mu_n'],sim.mesh.fields['mu_p'])
    low.set_effective_dos(np.full(size,density),np.full(size,density));low.set_bandgap(np.zeros(size))
    low.set_recombination(np.full(size,1e100),np.full(size,1e100))
    contacts=np.flatnonzero(sim.mesh.fields['contact_low']|sim.mesh.fields['contact_high']);phi=bias*(1-x/.6e-6)
    low.set_dirichlet_potential({int(i):float(phi[i]) for i in contacts})
    low.set_electron_bc({int(i):density for i in contacts});low.set_hole_bc({int(i):density for i in contacts})
    low.set_initial_guess(phi,np.full(size,density),np.full(size,density));low.set_use_newton(False)
    state=sim.run(max_iter=80,tol=1e-12,physical_step=False)
    assert state['converged']
    before=contact_current_1d(sim,state,'low');legacy=attribute_mechanism(sim,state)
    report=density_report(sim,state,1e-12)
    assert report.J_drift==legacy.J_drift and report.J_diff==legacy.J_diff
    assert report.J_drift==pytest.approx(abs(before),rel=2e-10)
    assert report.J_btbt==report.J_fe==0. and report.weights_available
    assert contact_current_1d(sim,state,'low')==before


if __name__=='__main__':
    Path(sys.argv[1]).write_text(json.dumps(dict(constants=native_constants(),records=[record(*case) for case in CASES]),indent=2))
