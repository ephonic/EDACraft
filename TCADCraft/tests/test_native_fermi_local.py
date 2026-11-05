"""Native FD thermodynamics and actual local n,p,T conservation rows."""
from copy import deepcopy
import numpy as np
import pytest
from tcad.core import native_precision
from tcad.core._bindings import native_fermi_reservoir_raw,native_fermi_local_raw
from tcad.physics.native_fermi_local import native_fermi_reservoirs,_decimal
from tcad.postprocess.fermi_spectral_energy import reference_reservoir,audit_fermi_spectral_energy
from tcad.physics.multivalley_thermionic import ThermionicValley,Q
from tcad.solver.fermi_electrothermal import FermiSpectralElectrothermal
from test_fermi_spectral import fixture,VALLEYS,BUDGET
from test_native_spectral import constructor_arguments


@pytest.mark.parametrize('density',[1e17,1e24,2e25,1e26])
@pytest.mark.parametrize('T',[300.,450.])
def test_native_FD_reservoir_matches_independent_DOS_quadrature(density,T):
    actual=native_fermi_reservoirs([density],[T],[.04*Q],VALLEYS)[0]
    expected=reference_reservoir(density,T,.04*Q,VALLEYS)
    assert actual['density_m3']==pytest.approx(density,rel=2e-14)
    for key in ('chemical_potential_J','energy_density_J_m3'):
        assert actual[key]==pytest.approx(expected[key],rel=2e-9,abs=1e-32)
    assert sum(actual['valley_densities_m3'])==pytest.approx(density,rel=2e-14)
    assert actual['execution_backend']=='native' and native_precision()['mantissa_bits']==113


def test_native_FD_offset_valleys_and_batch_order():
    valleys=(ThermionicValley('a',2,.916,.190,.190),
        ThermionicValley('b',4,.190,.916,.190,band_offset_owner_J=.03*Q,band_offset_neighbor_J=.03*Q))
    ns=[1e17,1e25,1e26];Ts=[450.,300.,375.];bands=[-.02*Q,.04*Q,.01*Q]
    rows=native_fermi_reservoirs(ns,Ts,bands,valleys)
    for n,T,band,row in zip(ns,Ts,bands,rows):
        expected=reference_reservoir(n,T,band,valleys)
        assert row['chemical_potential_J']==pytest.approx(expected['chemical_potential_J'],rel=2e-9,abs=1e-32)
        assert row['energy_density_J_m3']==pytest.approx(expected['energy_density_J_m3'],rel=2e-9,abs=1e-32)


def test_native_local_boundary_preserves_sub_float64_density_difference():
    before=np.longdouble('1e26');after=before+np.longdouble('1e9');vol=1e-22
    assert after!=before and float(after)==float(before)
    cells=[before,before,300.,after,before,300.,1e6,1e6,vol,1e6,0.,0.,1.]
    faces=[0,-1,0,0,0,0,0,1e-14,1e-8,0,300,0]
    values=native_fermi_local_raw(list(map(_decimal,cells)),list(map(_decimal,faces)),1e-13)
    assert values[0]==pytest.approx(float((after-before)*vol),rel=1e-14)
    assert values[0]!=0 and values[1:]==[0.]*6


def test_native_local_Fourier_storage_and_work_match_hand_computation():
    # Two cells, one internal edge; no bath. All values here are exact binary.
    cells=[8,8,2,9,7,4,16,32,.5,4,0,2,2,
           8,8,8,7,9,6,32,16,.5,4,4,6,2]
    faces=[0,1,2,4,8,2,4,2,.5,.5,0,0]
    actual=native_fermi_local_raw(list(map(str,cells)),list(map(str,faces)),.25)
    heat=2*2/(.5+.5)*(4-6)
    work=np.array([.25*Q*(4-2)*(1-3),-.25*Q*(4-2)*(5-3)])
    expected=np.r_[[1.,-1.],[.5,-.5],[8.,-8.],[4.,-4.],work,
        np.array([12.,-12.])+.25*np.array([8+heat,-8-heat])-work,heat]
    np.testing.assert_allclose(actual,expected,rtol=1e-14,atol=0.)


@pytest.mark.parametrize('scale,voltage,count,contacts',[(1.,0.,2,False),(1.,.002,2,True),
    (1.,-.002,2,True),(10.,0.,2,True),(10.,.002,2,True),(10.,-.002,2,True),
    (10.,.002,4,True),(10.,-.002,4,True)])
def test_actual_native_local_continuous_steps_pass_independent_audit(scale,voltage,count,contacts):
    model,state=fixture(contacts=contacts,voltage=voltage,count=count,density_scale=scale)
    model.spectral_backend=model.local_backend='native'
    for _ in range(2):
        old=state;state,report=model.step(old,2e-13,**BUDGET)
        audit=audit_fermi_spectral_energy(model,old,state,report,**BUDGET)
        assert audit['valid'],audit
        assert report['thermodynamic_backend']==report['local_backend']=='native'
        assert not report['native_nonlinear_driver']
        assert max(abs(state.temperature_K-old.temperature_K))>1e-6


def test_actual_native_local_path_runs_with_Python_thermodynamics_and_heat_disabled(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('Python production thermodynamics/heat invoked')
    model,old=fixture(contacts=True,voltage=.002,density_scale=10.)
    model.spectral_backend=model.local_backend='native'
    monkeypatch.setattr('tcad.solver.fermi_electrothermal.fermi_reservoir',forbidden)
    monkeypatch.setattr('tcad.physics.fermi_spectral.fermi_reservoir',forbidden)
    monkeypatch.setattr(model,'conduction',forbidden)
    monkeypatch.setattr('tcad.solver.fermi_electrothermal.spectral_face',forbidden)
    new,report=model.step(old,2e-13,**BUDGET)
    assert audit_fermi_spectral_energy(model,old,new,report,**BUDGET)['valid']


def test_constructor_native_local_and_strict_missing_symbol(monkeypatch):
    mesh,old,kwargs=constructor_arguments()
    model=FermiSpectralElectrothermal(mesh,spectral_backend='native',local_backend='native',**kwargs)
    new,report=model.step(old,2e-13,**BUDGET)
    assert audit_fermi_spectral_energy(model,old,new,report,**BUDGET)['valid']
    with pytest.raises(ValueError,match='local_backend'):
        FermiSpectralElectrothermal(mesh,local_backend='native',**kwargs)
    with pytest.raises(ValueError,match='local_backend'):
        FermiSpectralElectrothermal(mesh,local_backend='automatic',**kwargs)
    monkeypatch.delattr('tcad.core._bindings.native_fermi_local_raw')
    with pytest.raises(ImportError):
        FermiSpectralElectrothermal(mesh,spectral_backend='native',local_backend='native',**kwargs)


@pytest.mark.parametrize('field',['local_backend','thermodynamic_backend'])
def test_independent_audit_rejects_false_local_execution_claim(field):
    model,old=fixture();model.spectral_backend=model.local_backend='native'
    new,report=model.step(old,2e-13,**BUDGET);bad=deepcopy(report);bad[field]='python'
    assert not audit_fermi_spectral_energy(model,old,new,bad,**BUDGET)['valid']


def test_native_local_rejected_step_does_not_modify_input_state():
    model,old=fixture(contacts=True,voltage=.002,density_scale=10.)
    model.spectral_backend=model.local_backend='native'
    snapshot=[getattr(old,k).tobytes() for k in ('n_m3','p_m3','temperature_K','trap_fraction')]
    with pytest.raises(ValueError):model.step(old,2e-13,max_nfev=1,**BUDGET)
    assert snapshot==[getattr(old,k).tobytes() for k in ('n_m3','p_m3','temperature_K','trap_fraction')]
    assert old.time_s==0.


@pytest.mark.parametrize('states,valleys',[
    ([],[1.,1.,2.,0.]),(['1','300'],[1.,1.,2.,0.]),(['-1','300','0'],[1.,1.,2.,0.]),
    (['1','0','0'],[1.,1.,2.,0.]),(['NaN','300','0'],[1.,1.,2.,0.]),
    (['1junk','300','0'],[1.,1.,2.,0.]),(['1\x00junk','300','0'],[1.,1.,2.,0.]),
    (['1','300','0'],[1.,0.,2.,0.]),(['1','300','0'],[1.,1.,2.])])
def test_native_reservoir_raw_rejects_invalid_inputs(states,valleys):
    with pytest.raises(ValueError):native_fermi_reservoir_raw(states,valleys)


@pytest.mark.parametrize('damage',['size','owner','neighbor','fractional','distance','bath','volume','nan','dt'])
def test_native_local_raw_rejects_invalid_inputs(damage):
    cells=list(map(str,[1,1,300,1,1,300,1,1,1,1,0,0,1]))
    faces=list(map(str,[0,-1,0,0,0,0,0,1,1,0,300,1]));dt=1e-13
    if damage=='size':cells.pop()
    elif damage=='owner':faces[0]='1'
    elif damage=='neighbor':faces[1]='-2'
    elif damage=='fractional':faces[0]='.5'
    elif damage=='distance':faces[8]='0'
    elif damage=='bath':faces[10]='-1'
    elif damage=='volume':cells[8]='0'
    elif damage=='nan':cells[3]='nan'
    else:dt=0.
    with pytest.raises(ValueError):native_fermi_local_raw(cells,faces,dt)
