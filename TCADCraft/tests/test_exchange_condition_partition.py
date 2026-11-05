"""Whole a/c conditions survive renaming, resampling and cross-species exports."""
from pathlib import Path
from dataclasses import replace
import hashlib,importlib.util,sys
import numpy as np
import pytest
from tcad.material import energy_relaxation_calibration as current
from test_energy_relaxation_calibration import observations,TRUTH

OUT=Path(__file__).resolve().parents[1]/'docs/validation/exchange_condition_partition_20261022'
ADDED={'whole_condition_holdout_checked','whole_condition_partition'}
VARIANTS=['renamed_export','different_Tc','reversed_samples','subset_samples','scaled_exchange',
          'different_uncertainty','different_reference','one_overlapping_row']


def parent():
 name='tcad.material.frozen_exchange_partition_parent'
 spec=importlib.util.spec_from_file_location(name,OUT/'before/tcad/material/energy_relaxation_calibration.py')
 m=importlib.util.module_from_spec(spec);sys.modules[name]=m
 previous=sys.dont_write_bytecode;sys.dont_write_bytecode=True
 try:spec.loader.exec_module(m)
 finally:sys.dont_write_bytecode=previous
 return m


def old_fit(data,**kwargs):
 m=parent()
 return m.calibrate_energy_relaxation_power_law([m.RelaxationExchangeCondition(**{
  k:getattr(c,k) for k in m.RelaxationExchangeCondition.__dataclass_fields__}) for c in data],**kwargs)


def exchange(c,*,Tc=None,L=None,N=None,scale=1.,sigma=None):
 Tc=c.carrier_temperature_K if Tc is None else np.asarray(Tc)
 L=c.lattice_temperature_K if L is None else np.asarray(L)
 N=c.density_m3 if N is None else np.asarray(N)
 tau0,a,b,d=TRUTH[c.carrier]
 tau=tau0*(L/300.)**a*(Tc/300.)**b*(N/1e25)**d
 du=scale*(Tc-L)*N*1.5*1.380649e-23
 return replace(c,carrier_temperature_K=Tc,lattice_temperature_K=L,density_m3=N,
  energy_difference_J_m3=du,power_to_lattice_W_m3=du/tau,
  log_tau_standard_uncertainty=np.full(len(Tc),.01 if sigma is None else sigma))


def leaking(index,variant):
 data=observations();held=data[index];source=data[index-4]
 row=replace(source,condition_id=held.condition_id,source_sha256=held.source_sha256,role='holdout')
 if variant=='different_Tc':row=exchange(row,Tc=[270.,310.,390.],L=np.full(3,source.lattice_temperature_K[0]),N=np.full(3,source.density_m3[0]))
 elif variant=='reversed_samples':row=exchange(row,Tc=row.carrier_temperature_K[::-1])
 elif variant=='subset_samples':row=exchange(row,Tc=row.carrier_temperature_K[:3],L=row.lattice_temperature_K[:3],N=row.density_m3[:3])
 elif variant=='scaled_exchange':row=exchange(row,scale=1.4)
 elif variant=='different_uncertainty':row=exchange(row,sigma=.02)
 elif variant=='different_reference':row=replace(row,source_reference='test: independent renamed source label')
 elif variant=='one_overlapping_row':
  N=held.density_m3.copy();L=held.lattice_temperature_K.copy()
  N[1]=source.density_m3[0];L[1]=source.lattice_temperature_K[0]
  row=exchange(held,N=N,L=L)
 data[index]=row
 return data


@pytest.mark.parametrize('index',[4,9])
@pytest.mark.parametrize('variant',VARIANTS)
def test_same_ac_pair_is_rejected_before_linear_algebra(index,variant,monkeypatch):
 data=leaking(index,variant);old=old_fit(data)
 assert old['fit_accepted'] and old['holdouts_accepted'] and old['training_accepted']
 def forbidden(*a,**kw):raise AssertionError('leaking a/c conditions reached SVD')
 monkeypatch.setattr(current.np.linalg,'svd',forbidden)
 with pytest.raises(ValueError,match='condition crosses calibration/holdout roles'):
  current.calibrate_energy_relaxation_power_law(data)


@pytest.mark.parametrize('index',[0,1,5,6])
def test_cross_species_split_cannot_be_hidden_by_new_id_and_hash(index,monkeypatch):
 data=observations();name='relabeled-'+str(index)
 data[index]=replace(data[index],condition_id=name,source_sha256=hashlib.sha256(name.encode()).hexdigest(),role='holdout')
 assert old_fit(data)['fit_accepted']
 def forbidden(*a,**kw):raise AssertionError('cross-species split reached SVD')
 monkeypatch.setattr(current.np.linalg,'svd',forbidden)
 with pytest.raises(ValueError,match='condition crosses calibration/holdout roles'):
  current.calibrate_energy_relaxation_power_law(data)


@pytest.mark.parametrize('index',[0,4])
def test_independent_replicates_remain_in_their_original_role(index):
 data=observations();name='repeat-'+str(index)
 data.append(replace(data[index],condition_id=name,source_sha256=hashlib.sha256(name.encode()).hexdigest()))
 report=current.calibrate_energy_relaxation_power_law(data)
 assert report['fit_accepted']
 assert {k:v for k,v in report.items() if k not in ADDED}==old_fit(data)
 group=next(g for g in report['whole_condition_partition']['groups'] if name in g['condition_ids'])
 assert group['role']==data[index].role and group['observations']==len(data[index].density_m3)*3


@pytest.mark.parametrize('L,N',[(280.,1e25),(300.,8e24)])
def test_new_pair_can_share_one_training_axis(L,N):
 data=observations()
 for index in (4,9):data[index]=exchange(data[index],L=np.full(3,L),N=np.full(3,N))
 report=current.calibrate_energy_relaxation_power_law(data)
 assert report['fit_accepted']
 assert {k:v for k,v in report.items() if k not in ADDED}==old_fit(data)


@pytest.mark.parametrize('kind',['base','failed_holdout','training_misfit','reparameterized'])
def test_all_old_fields_and_fit_parameters_are_exact(kind):
 data=observations();kw={}
 if kind=='failed_holdout':data[4]=replace(data[4],power_to_lattice_W_m3=data[4].power_to_lattice_W_m3*2)
 if kind=='training_misfit':
  power=data[0].power_to_lattice_W_m3.copy();power[0]*=1.2;data[0]=replace(data[0],power_to_lattice_W_m3=power)
 if kind=='reparameterized':kw=dict(reference_temperature_K=320.,reference_density_m3=1.1e25)
 before=[tuple(getattr(c,k).tobytes() for k in ('density_m3','carrier_temperature_K','lattice_temperature_K','energy_difference_J_m3','power_to_lattice_W_m3')) for c in data]
 report=current.calibrate_energy_relaxation_power_law(data,**kw)
 assert {k:v for k,v in report.items() if k not in ADDED}==old_fit(data,**kw)
 assert before==[tuple(getattr(c,k).tobytes() for k in ('density_m3','carrier_temperature_K','lattice_temperature_K','energy_difference_J_m3','power_to_lattice_W_m3')) for c in data]


def test_partition_is_deterministic_and_does_not_authenticate_measurements():
 data=observations();report=current.calibrate_energy_relaxation_power_law(data)
 partition=report['whole_condition_partition']
 assert partition==current.calibrate_energy_relaxation_power_law(data[::-1])['whole_condition_partition']
 assert report['whole_condition_holdout_checked'] and partition['grouped_across_carriers']
 assert partition['condition_axes']==['lattice_temperature_K','density_m3'] and len(partition['groups'])==5
 assert all(g['carriers']==['electrons','holes'] for g in partition['groups'])
 assert not report['physical_validated'] and not report['experimental_validated'] and not report['provenance_authenticated']


def test_unpaired_holdouts_do_not_invent_missing_carrier_observations():
 data=observations();data[9]=exchange(data[9],L=np.full(3,310.))
 report=current.calibrate_energy_relaxation_power_law(data)
 assert report['fit_accepted']
 held=[g for g in report['whole_condition_partition']['groups'] if g['role']=='holdout']
 assert len(held)==2 and all(len(g['carriers'])==1 for g in held)
 assert not report['experimental_validated']
