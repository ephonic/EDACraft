"""Nonfinite evidence must not disappear inside independent audit reductions."""
from pathlib import Path
from copy import deepcopy
import importlib.util,json,sys
import numpy as np
import pytest
from test_energy_coordinate_transport import transport_case,BUDGET
from tcad.postprocess import energy_coordinate_transport as current
from tcad.postprocess.device_energy_coordinate_transport import audit_device_energy_coordinate_step,METADATA
from tcad.solver.energy_coordinate_transport import initialize_energy_coordinates,energy_coordinate_step,EnergyCoordinateState,SCOPE
from tcad.solver.device_energy_coordinate_transport import DeviceEnergyCoordinateTransport
from tcad.solver.three_temperature import ThreeTemperatureState

OUT=Path(__file__).resolve().parents[1]/'docs/validation/energy_record_finite_20261022'
DAMAGE=([f'ledger_{i}' for i in (0,1,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19)]
 +[f'cell_{i}' for i in (6,7,9,10,14,15)]+['face_6','face_7','codec_1','codec_7',
 'moment_e','moment_h','newton_stat_1','newton_stat_2','newton_stat_3','newton_state'])


def parent():
 name='tcad.postprocess.frozen_energy_finite_parent'
 spec=importlib.util.spec_from_file_location(name,OUT/'before/tcad/postprocess/energy_coordinate_transport.py')
 m=importlib.util.module_from_spec(spec);sys.modules[name]=m
 previous=sys.dont_write_bytecode;sys.dont_write_bytecode=True
 try:spec.loader.exec_module(m)
 finally:sys.dont_write_bytecode=previous
 return m


def old_audit(mode,model,old,new,report,module=None):
 m=parent() if module is None else module
 if mode=='functional':return m.audit_energy_coordinate_step(model,old,new,report,**BUDGET)
 mathematical={k:v for k,v in report.items() if k not in METADATA}
 mathematical['scope']=SCOPE;mathematical['native_device_session_integrated']=False
 return dict(m.audit_energy_coordinate_step(model,old,new,mathematical,**BUDGET),native_device_session_integrated=True)


def audit(mode,*args):
 return (current.audit_energy_coordinate_step if mode=='functional' else audit_device_energy_coordinate_step)(*args,**BUDGET)


def encode_state(state):
 fields={}
 for name in ('n_m3','p_m3','trap_fraction','temperature_K','electron_temperature_K','hole_temperature_K'):
  values=getattr(state.thermal,name)
  fields[name]=[np.format_float_scientific(v,precision=35,unique=False) for v in values] if name in ('n_m3','p_m3') else values.tolist()
 fields['time_s']=state.thermal.time_s
 return dict(thermal=fields,excess_J_m3=state.excess_J_m3,configuration_sha256=state.configuration_sha256)


def decode_state(data):
 fields=dict(data['thermal'])
 for name in ('n_m3','p_m3'):fields[name]=np.asarray(fields[name],np.longdouble)
 return EnergyCoordinateState(ThreeTemperatureState(**fields),tuple(data['excess_J_m3']),data['configuration_sha256'])


def captured(mode):
 data=json.loads((OUT/'accepted_records'/(mode+'.json')).read_text())
 model,_=transport_case()
 return model,decode_state(data['old']),decode_state(data['new']),data['report']


@pytest.fixture(scope='module',params=['functional','device'])
def accepted(request):
 mode=request.param;model,initial=transport_case()
 if mode=='functional':
  old=initialize_energy_coordinates(model,initial);new,report=energy_coordinate_step(model,old,2e-14,**BUDGET)
 else:
  device=DeviceEnergyCoordinateTransport(model,initial);old=device.state;new,report=device.advance(2e-14,**BUDGET)
 assert report['independent_audit']['valid'] and any(0<abs(np.longdouble(v))<np.longdouble('1e-70') for v in new.excess_J_m3)
 directory=OUT/'accepted_records';directory.mkdir(exist_ok=True)
 target=directory/(mode+'.json');assert not target.exists()
 target.write_text(json.dumps(dict(mode=mode,old=encode_state(old),new=encode_state(new),report=report,
  material_coefficients=dict(a=-20000,c=20000,b=0),native_advances=1),indent=2,allow_nan=False)+'\n')
 return mode,model,old,new,report


def damage(report,name,value):
 r=deepcopy(report);raw=r['raw'];text=str(value)
 if name.startswith('ledger_'):raw['ledger'][int(name.split('_')[1])]=text
 elif name.startswith('cell_'):raw['local_cells'][int(name.split('_')[1])]=text
 elif name.startswith('face_'):raw['local_faces'][int(name.split('_')[1])]=text
 elif name.startswith('codec_'):raw['temperature_cells'][int(name.split('_')[1])]=text
 elif name.startswith('moment_'):
  moments=raw['transport']['moments'];start=0 if name=='moment_e' else len(moments)//2
  index=next(i for i in range(start,start+len(moments)//2) if moments[i]);moments[index][3]=value
 elif name.startswith('newton_stat_'):raw['transport']['newton'][1][int(name.split('_')[-1])]=value
 else:raw['transport']['newton'][0][0]=value
 return r


@pytest.mark.parametrize('name',DAMAGE)
def test_old_nan_false_acceptance_is_rejected_before_reference_physics(accepted,name,monkeypatch):
 mode,model,old,new,report=accepted;r=damage(report,name,np.nan)
 with np.errstate(all='ignore'):before=old_audit(mode,model,old,new,r)
 assert before['valid'] and before['modeled_fixed_band_energy_closed'],(mode,name,before)
 def forbidden(*a,**k):raise AssertionError('nonfinite native evidence reached independent DOS')
 monkeypatch.setattr(current,'reference_reservoir',forbidden)
 with pytest.raises(ValueError,match='finite numeric native energy-coordinate record'):
  audit(mode,model,old,new,r)


@pytest.mark.parametrize('name',['ledger_14','cell_14','face_6','codec_1','moment_e','newton_stat_3'])
@pytest.mark.parametrize('value',[np.inf,-np.inf])
def test_infinite_records_are_rejected_in_each_record_family(accepted,name,value):
 mode,model,old,new,report=accepted
 with pytest.raises(ValueError,match='finite numeric native energy-coordinate record'):
  audit(mode,model,old,new,damage(report,name,value))


def test_normal_complete_report_and_inputs_remain_exact(accepted):
 mode,model,old,new,report=accepted;before=deepcopy(report)
 assert audit(mode,model,old,new,report)==old_audit(mode,model,old,new,report)==report['independent_audit']
 assert report==before
 replay=captured(mode)
 assert audit(mode,*replay)==report['independent_audit']


def test_independent_replay_calls_no_native_operators(accepted,monkeypatch):
 mode,model,old,new,report=accepted
 import tcad.core._bindings as native
 def forbidden(*a,**k):raise AssertionError('production native operator called during audit')
 for name in dir(native):
  if name.startswith('native_') and callable(getattr(native,name)):monkeypatch.setattr(native,name,forbidden)
 assert audit(mode,model,old,new,report)==report['independent_audit']


def test_reconstructed_nan_entropy_cannot_hide_in_a_reduction(accepted,monkeypatch):
 mode,model,old,new,report=accepted;m=parent();reference=current.reference_face
 def nonfinite(*a,**k):
  result=dict(reference(*a,**k));result['entropy_production_W_K']=np.nan;return result
 monkeypatch.setattr(m,'reference_face',nonfinite)
 with np.errstate(all='ignore'):assert old_audit(mode,model,old,new,report,module=m)['valid']
 monkeypatch.setattr(current,'reference_face',nonfinite)
 with pytest.raises(ValueError,match='nonfinite independently reconstructed'):
  audit(mode,model,old,new,report)
