"""Executable native spectral moments and their actual coupled device path."""
from copy import deepcopy
import numpy as np
import pytest
from tcad.core import native_precision
from tcad.core._bindings import native_spectral_face_raw
from tcad.physics.fermi_spectral import fermi_reservoir,spectral_face
from tcad.physics.native_spectral import native_spectral_face
from tcad.postprocess.fermi_spectral_energy import reference_face,audit_fermi_spectral_energy
from test_fermi_spectral import fixture,VALLEYS,BUDGET
from tcad.solver.fermi_electrothermal import FermiSpectralElectrothermal


def arguments(A=2.,reverse=False):
    one=fermi_reservoir(2e25,450. if reverse else 300.,.02*1.602176634e-19,VALLEYS)
    two=fermi_reservoir(8e24,300. if reverse else 450.,.06*1.602176634e-19,VALLEYS)
    kwargs=dict(potential_owner_V=0.,potential_neighbor_V=.002,potential_face_V=.001,charge_sign=-1,
        mobility_owner_m2_Vs=.01,mobility_neighbor_m2_Vs=.02,area_m2=1e-14,
        distance_owner_m=2e-8,distance_neighbor_m=3e-8,emission_factor=A)
    return one,two,kwargs


@pytest.mark.parametrize('A',[None,0.,.5,2.])
@pytest.mark.parametrize('reverse',[False,True])
def test_native_moments_match_independent_adaptive_quadrature(A,reverse):
    one,two,kwargs=arguments(A,reverse)
    actual=native_spectral_face(one,two,VALLEYS,**kwargs)
    expected=reference_face(one,two,VALLEYS,phi_o=0.,phi_n=.002,phi_f=.001,z=-1,
        mu_o=.01,mu_n=.02,area=1e-14,do=2e-8,dn=3e-8,A=A)
    for key in ('particle_flux_s','total_energy_flux_W','material_energy_flux_W','entropy_production_W_K'):
        assert actual[key]==pytest.approx(expected[key],rel=2e-8,abs=1e-30),key
    assert actual['entropy_production_W_K']>=0.
    assert 0<=actual['trace_occupation_min']<=actual['trace_occupation_max']<=1.
    assert actual['execution_backend']=='native'
    assert native_precision()['mantissa_bits']==113


@pytest.mark.parametrize('A',[None,0.,2.])
def test_native_face_reversal_and_gauge_invariance(A):
    one,two,kwargs=arguments(A)
    original=native_spectral_face(one,two,VALLEYS,**kwargs)
    reverse=dict(kwargs,potential_owner_V=.002,potential_neighbor_V=0.,
        mobility_owner_m2_Vs=.02,mobility_neighbor_m2_Vs=.01,distance_owner_m=3e-8,distance_neighbor_m=2e-8)
    flipped=native_spectral_face(two,one,VALLEYS,**reverse)
    gauge=dict(kwargs,potential_owner_V=.3,potential_neighbor_V=.302,potential_face_V=.301)
    shifted=native_spectral_face(one,two,VALLEYS,**gauge)
    for key in ('particle_flux_s','material_energy_flux_W'):
        assert flipped[key]==pytest.approx(-original[key],rel=2e-12,abs=1e-30)
        assert shifted[key]==pytest.approx(original[key],rel=2e-12,abs=1e-30)
    assert flipped['entropy_production_W_K']==pytest.approx(original['entropy_production_W_K'],rel=2e-12)


@pytest.mark.parametrize('scale,voltage,count',[(1.,0.,2),(1.,.002,2),(1.,-.002,2),
    (10.,0.,2),(10.,.002,2),(10.,-.002,2),(10.,.002,4),(10.,-.002,4)])
def test_native_constitutive_law_participates_in_actual_coupled_steps(scale,voltage,count):
    model,state=fixture(contacts=True,voltage=voltage,count=count,density_scale=scale)
    model.spectral_backend='native'
    for _ in range(2):
        old=state;state,report=model.step(old,2e-13,**BUDGET)
        audit=audit_fermi_spectral_energy(model,old,state,report,**BUDGET)
        assert audit['valid'],audit
        assert report['spectral_backend']=='native' and not report['native_nonlinear_driver']
        assert max(abs(state.temperature_K-old.temperature_K))>1e-6
        assert all(row['execution_backend']=='native' for rows in report['face_moments'].values() for row in rows.values())


def test_native_path_has_no_python_spectral_fallback(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('Python face law invoked')
    monkeypatch.setattr('tcad.solver.fermi_electrothermal.spectral_face',forbidden)
    monkeypatch.setattr('tcad.physics.fermi_spectral.spectral_face',forbidden)
    model,old=fixture(contacts=True,voltage=.002,density_scale=10.)
    model.spectral_backend='native';new,report=model.step(old,2e-13,**BUDGET)
    assert audit_fermi_spectral_energy(model,old,new,report,**BUDGET)['valid']


def constructor_arguments():
    model,state=fixture()
    return model.mesh,state,dict(permittivity_F_m=1e-10,dirichlet_V=model.bc,
        mobility_n_m2_Vs=.01,mobility_p_m2_Vs=.01,Ec_J=model.Ec,Eh_J=model.Eh,
        heat_capacity_J_m3_K=model.capacity,thermal_conductivity_W_m_K=model.conductivity,
        valleys_n=VALLEYS,valleys_p=VALLEYS,thermionic_faces=model.thermionic_faces)


def test_constructor_selects_native_backend_for_actual_step():
    mesh,old,kwargs=constructor_arguments()
    model=FermiSpectralElectrothermal(mesh,spectral_backend='native',**kwargs)
    new,report=model.step(old,2e-13,**BUDGET)
    assert report['spectral_backend']=='native'
    assert audit_fermi_spectral_energy(model,old,new,report,**BUDGET)['valid']


def test_constructor_rejects_unknown_or_unavailable_backend(monkeypatch):
    mesh,_,kwargs=constructor_arguments()
    with pytest.raises(ValueError,match='spectral_backend'):
        FermiSpectralElectrothermal(mesh,spectral_backend='automatic',**kwargs)
    monkeypatch.delattr('tcad.core._bindings.native_spectral_face_raw')
    with pytest.raises(ImportError):FermiSpectralElectrothermal(mesh,spectral_backend='native',**kwargs)


@pytest.mark.parametrize('field',['spectral_backend','native_nonlinear_driver','face_backend'])
def test_audit_rejects_false_native_execution_claims(field):
    model,old=fixture();model.spectral_backend='native'
    new,report=model.step(old,2e-13,**BUDGET);bad=deepcopy(report)
    if field=='face_backend':next(iter(bad['face_moments']['electrons'].values()))['execution_backend']='python'
    else:bad[field]='python' if field=='spectral_backend' else True
    assert not audit_fermi_spectral_energy(model,old,new,bad,**BUDGET)['valid']


@pytest.mark.parametrize('damage',['size','valleys','temperature','mobility','distance','emission','sign','nan'])
def test_native_raw_boundary_rejects_invalid_values(damage):
    inputs=[300.,450.,1e-20,2e-20,0.,0.,0.,0.,0.,-1.,.01,.02,1e-14,2e-8,3e-8,1.,2.]
    valleys=[.916,.3,2.,0.]
    if damage=='size':inputs.pop()
    elif damage=='valleys':valleys.pop()
    else:
        index,value={'temperature':(0,-1.),'mobility':(10,0.),'distance':(14,0.),
            'emission':(16,-1.),'sign':(9,0.),'nan':(6,float('nan'))}[damage]
        inputs[index]=value
    with pytest.raises(ValueError):native_spectral_face_raw(inputs,valleys)
