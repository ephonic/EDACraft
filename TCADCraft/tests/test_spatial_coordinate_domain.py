"""Original domain and representable interpolation intervals for 3T profiles."""
from pathlib import Path
from copy import deepcopy
import importlib.util,sys
import numpy as np
import pytest
from tcad.postprocess import spatial_energy_transport as current
from test_spatial_energy_transport import profile

OUT=Path(__file__).resolve().parents[1]/'docs/validation/spatial_coordinate_domain_20261022'
KINDS=['overflow_interval']+[
 f'{container}_{side}' for container in ('list','int64','uint64','mixed') for side in ('above','below')
]+['reference_above','reference_below','extended_above','extended_below',
   'extended_reference_above','extended_reference_below','underflow_query','underflow_reference']


def parent():
 spec=importlib.util.spec_from_file_location('frozen_spatial_coordinate_parent',OUT/'before/tcad/postprocess/spatial_energy_transport.py')
 module=importlib.util.module_from_spec(spec)
 old=sys.dont_write_bytecode;sys.dont_write_bytecode=True
 try:spec.loader.exec_module(module)
 finally:sys.dont_write_bytecode=old
 return module


def inputs(kind):
 p=profile('synthetic-'+kind,'holdout')
 if kind=='overflow_interval':
  xr=np.r_[-1e308,1e308,np.linspace(1.1e308,1.7e308,7)];x=[0.,5e307]
 elif kind.startswith(('list_','int64_','uint64_','mixed_')):
  container,side=kind.split('_')
  if side=='above':xr=[2**53-32+4*i for i in range(9)];x=[2**53-4,2**53+1]
  else:xr=[2**54+4*i for i in range(9)];x=[2**54-1,2**54+4]
  if container in ('int64','uint64'):x=np.array(x,dtype=container);xr=np.array(xr,dtype=container)
  elif container=='mixed':x[0 if side=='above' else 1]=float(x[0 if side=='above' else 1])
 elif kind=='reference_above':
  xr=[2**53-60+8*i for i in range(9)];xr[-1]-=1;x=[2**53,2**53+4]
 elif kind=='reference_below':
  xr=[2**54+8*i for i in range(9)];xr[0]+=1;x=[2**54,2**54+8]
 else:
  assert np.finfo(np.longdouble).nmant>np.finfo(float).nmant
  xr=np.linspace(1.,2.,9,dtype=np.longdouble);x=np.array([1.25,1.75],dtype=np.longdouble)
  if kind=='extended_above':x[-1]=np.nextafter(np.longdouble(2),np.longdouble(3))
  elif kind=='extended_below':x[0]=np.nextafter(np.longdouble(1),np.longdouble(0))
  elif kind=='extended_reference_above':xr[-1]=np.nextafter(np.longdouble(2),np.longdouble(1));x[-1]=2
  elif kind=='extended_reference_below':xr[0]=np.nextafter(np.longdouble(1),np.longdouble(2));x[0]=1
  else:
   xr=np.linspace(0.,1.,9,dtype=np.longdouble);x=np.array([.25,.75],dtype=np.longdouble)
   tiny=np.nextafter(np.longdouble(0),np.longdouble(1))
   if kind=='underflow_query':x[0]=tiny
   else:xr[0]=tiny
 p['x_m']=xr;n=len(xr)
 for k in ('Tn_K','Tp_K','Tl_K'):p[k]=np.r_[600.,np.full(n-1,601.)]
 for k in ('n_m3','p_m3','mu_n_m2_Vs','mu_p_m2_Vs','Fn_m2_s','Fp_m2_s','Sn_W_m2','Sp_W_m2'):p[k]=np.ones(n)
 t={k:np.interp(np.asarray(x,dtype=float),np.asarray(xr,dtype=float),p[k]) for k in ('Tn_K','Tp_K','Tl_K')}
 return x,t,p


@pytest.mark.parametrize('kind',KINDS)
def test_old_false_acceptance_of_invalid_coordinates_is_rejected(kind):
 x,t,p=inputs(kind)
 with np.errstate(all='ignore'):old=parent().compare_temperature_profiles(x,t,p,bath_K=600.,require_resolved=True)
 assert old['accepted'] and old['all_three_temperatures_resolved']
 with pytest.raises(ValueError):current.compare_temperature_profiles(x,t,p,bath_K=600.,require_resolved=True)
 if kind=='overflow_interval':
  # Correct linear fractions are 1/2 and 3/4, far beyond the 0.101 K budget.
  np.testing.assert_equal(t['Tn_K'],[600.,600.])
  assert np.max(np.abs(t['Tn_K']-np.array([600.5,600.75])))>.101


@pytest.mark.parametrize('kind',['overflow_interval','underflow_reference'])
def test_shared_profile_validator_rejects_invalid_interpolation_grid(kind):
 with pytest.raises(ValueError):current.validate_spatial_profile(inputs(kind)[2])


@pytest.mark.parametrize('where',['reference','query'])
@pytest.mark.parametrize('bad',['duplicate','decreasing','nan','infinity','complex','boolean','short'])
def test_grid_contract_rejects_invalid_coordinates(where,bad):
 p=profile('normal','holdout');x=np.linspace(1e-9,99e-9,17)
 target=np.asarray(p['x_m'] if where=='reference' else x).copy()
 if bad=='duplicate':target[1]=target[0]
 elif bad=='decreasing':target=target[::-1]
 elif bad=='nan':target[1]=np.nan
 elif bad=='infinity':target[1]=np.inf
 elif bad=='complex':target=target.astype(complex)
 elif bad=='boolean':target=np.ones(len(target),dtype=bool)
 else:target=target[:8 if where=='reference' else 1]
 if where=='reference':p['x_m']=target
 else:x=target
 t={k:np.full(len(x),600.) for k in ('Tn_K','Tp_K','Tl_K')}
 with pytest.raises(ValueError):current.compare_temperature_profiles(x,t,p,bath_K=600.)


@pytest.mark.parametrize('kind',['normal','wrong_temperature','unresolved','exact_endpoints','integer_interior'])
def test_valid_reports_remain_exact_and_inputs_are_unchanged(kind):
 p=profile('normal','holdout');x=np.linspace(1e-9,99e-9,17)
 if kind=='exact_endpoints':x=np.array([p['x_m'][0],p['x_m'][-1]])
 if kind=='integer_interior':p['x_m']=np.arange(129,dtype=np.uint64)+np.uint64(2**52);p['x_m']*=np.uint64(4);x=p['x_m'][1:-1:8]
 t={k:np.interp(x,p['x_m'],p[k]) for k in ('Tn_K','Tp_K','Tl_K')}
 if kind=='wrong_temperature':t['Tl_K'][3]+=.1
 if kind=='unresolved':p['Tl_K'][:]=600.;t['Tl_K'][:]=600.
 snapshot=deepcopy((x,t,p))
 for strict in (False,True):
  assert current.compare_temperature_profiles(x,t,p,bath_K=600.,require_resolved=strict)==parent().compare_temperature_profiles(x,t,p,bath_K=600.,require_resolved=strict)
 for a,b in zip((x,t,p),snapshot):
  if isinstance(a,dict):
   for k in a:np.testing.assert_equal(a[k],b[k])
  else:np.testing.assert_equal(a,b)
