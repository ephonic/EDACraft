"""Positive RTA resistance integrated over a linear electrostatic path."""
import numpy as np
import pytest
from scipy.integrate import quad
from tcad.physics.fermi_spectral import fermi_reservoir,spectral_face,KB,Q,H,M0
from tcad.physics.native_spectral import native_spectral_face
from tcad.physics.multivalley_thermionic import ThermionicValley
from tcad.postprocess.fermi_spectral_energy import reference_face
from tcad.postprocess.three_temperature_energy import audit_three_temperature_energy
from test_smooth_temperature_bands import smooth_case
from test_three_temperature import BUDGET
V=(ThermionicValley('v',1.,1.,1.,1.),)
def face_data(x=.2,dn=1e-8,hot=False):
 a=fermi_reservoir(1e15,300.,.1*Q,V);b=fermi_reservoir(1e15,340. if hot else 300.,.1*Q,V)
 kw=dict(potential_owner_V=0.,potential_neighbor_V=-x*KB*300/Q,potential_face_V=-x*KB*150/Q,
  charge_sign=-1,mobility_owner_m2_Vs=.01,mobility_neighbor_m2_Vs=.007 if hot else .01,
  area_m2=1e-14,distance_owner_m=1e-8,distance_neighbor_m=dn)
 return a,b,kw
@pytest.mark.parametrize('x,dn,hot',[(0.,1e-8,False),(.2,1e-8,True),(-.2,2e-8,True),(.2,0.,True)])
def test_native_python_and_independent_adaptive_energy_moments(x,dn,hot):
 a,b,k=face_data(x,dn,hot);p=spectral_face(a,b,V,**k,bulk_potential_path='linear_series')
 n=native_spectral_face(a,b,V,**k,bulk_potential_path='linear_series')
 r=reference_face(a,b,V,phi_o=k['potential_owner_V'],phi_n=k['potential_neighbor_V'],phi_f=k['potential_face_V'],z=-1,
  mu_o=k['mobility_owner_m2_Vs'],mu_n=k['mobility_neighbor_m2_Vs'],area=k['area_m2'],
  do=k['distance_owner_m'],dn=dn,bulk_potential_path='linear_series')
 for key in ('particle_flux_s','total_energy_flux_W','material_energy_flux_W','entropy_production_W_K'):
  np.testing.assert_allclose(n[key],r[key],rtol=4e-10,atol=1e-28 if 'energy' in key or 'entropy' in key else 1e-7)
  np.testing.assert_allclose(p[key],r[key],rtol=4e-10,atol=1e-28 if 'energy' in key or 'entropy' in key else 1e-7)
 assert n['entropy_production_W_K']>=0 and 0<=n['trace_occupation_min']<=n['trace_occupation_max']<=1
 if x==0:
  legacy=native_spectral_face(a,b,V,**k)
  for key in ('particle_flux_s','total_energy_flux_W'):assert abs(n[key]-legacy[key])<1e-20

def test_linear_resistance_matches_direct_spatial_integral():
 # Nondimensional E above both endpoints; unequal half lengths and mobilities.
 for E in (.001,.1,1.,10.):
  uo,un=-.3,0.;do,dn=.7,.3;mo,mn=1.,.4;middle=uo+(un-uo)*do
  exact=quad(lambda x:1/((mo if x<do else mn)*(E-uo-(un-uo)*x)**1.5),0.,1.,points=[do],epsabs=1e-11,epsrel=1e-12)[0]
  def integral(d,mu,a,b):return 2*d/(mu*np.sqrt(E-a)*np.sqrt(E-b)*(np.sqrt(E-a)+np.sqrt(E-b)))
  np.testing.assert_allclose(integral(do,mo,uo,middle)+integral(dn,mn,middle,un),exact,rtol=2e-12)

def test_bulk_drift_continuum_error_decreases_faster_than_first_order():
 errors=[];old=[]
 for x in (.2,.1,.05):
  a,b,k=face_data(x);exact=-.01*1e15*(x*KB*300/Q)/(2e-8)*1e-14
  errors.append(abs(native_spectral_face(a,b,V,**k,bulk_potential_path='linear_series')['particle_flux_s']/exact-1))
  old.append(abs(native_spectral_face(a,b,V,**k)['particle_flux_s']/exact-1))
 assert errors[0]<.01 and errors[0]/errors[1]>3 and errors[1]/errors[2]>3
 assert old[0]>.09 and errors[-1]<old[-1]/50

@pytest.mark.parametrize('backend',['native','python'])
def test_actual_owned_band_gradient_step_and_forged_descriptor_rejected(backend,monkeypatch):
 from tcad.solver.device_three_temperature import DeviceThreeTemperature
 from copy import deepcopy
 model,initial=smooth_case();model.bulk_potential_path='linear_series'
 # Smooth temperature-dependent bands require native orchestration. Test the
 # Python residual path separately at fixed bands while retaining spectral primitives.
 if backend=='python':
  model.band_temperature_slopes=(np.zeros(model.nc),np.zeros(model.nc));model.residual_orchestration='python'
  new,report=model.step(initial,2e-13,**BUDGET)
 else:new,report=DeviceThreeTemperature(model,initial).advance(2e-13,**BUDGET,max_nfev=2000)
 assert report['bulk_potential_path']=='linear_series' and report['independent_audit']['valid']
 import tcad.core as public
 import tcad.core._bindings as native
 def deny(*a,**k):raise AssertionError('native call forbidden')
 for mod in (public,native):
  for name in dir(mod):
   if (name.startswith('native_') or name.startswith('three_temperature_')) and callable(getattr(mod,name)):monkeypatch.setattr(mod,name,deny)
 assert audit_three_temperature_energy(model,initial,new,report,**BUDGET)['valid']
 forged=deepcopy(report);forged['bulk_potential_path']='endpoint_barrier'
 with pytest.raises(ValueError,match='descriptor'):audit_three_temperature_energy(model,initial,new,forged,**BUDGET)

def test_mode_is_serialized_and_invalid_mode_rejected():
 from tcad.solver.native_three_temperature_dispatch import pack_three_temperature_inputs
 model,initial=smooth_case();model.bulk_potential_path='linear_series'
 args=pack_three_temperature_inputs(model,initial,2e-13,**BUDGET)
 assert all(float(args[1][22*f+19])==2 for f in range(len(model.mesh.faces)))
 model.bulk_potential_path='bad'
 with pytest.raises(ValueError,match='bulk_potential_path'):pack_three_temperature_inputs(model,initial,2e-13,**BUDGET)

def test_thermionic_emission_keeps_its_explicit_barrier_law():
 a,b,k=face_data(.2,hot=True)
 old=native_spectral_face(a,b,V,**k,emission_factor=.5)
 new=native_spectral_face(a,b,V,**k,emission_factor=.5,bulk_potential_path='linear_series')
 assert old==new
