"""Observe the retained initializer, then stop before its first DC factorization."""
from pathlib import Path
import hashlib,json,runpy,sys,time
import numpy as np
import sheet_runtime_profile_20261106 as profile
import tcad.solver.sheet_dielectric as dielectric
import tcad.solver._sheet_linear as linear

w=Path(sys.argv[1]);out=w/'artifacts';start=time.monotonic()
profile.install(out/'capture');context=dielectric.DielectricSheetDriftDiffusion._linear_context
geometry={}
def observe_geometry(self,*args,**kwargs):
    d=self.dielectric
    xyz=np.column_stack(np.unravel_index(np.arange(np.prod(d.shape)),d.shape))
    geometry['coordinates_zyx']=np.vstack([xyz[d.sheet_nodes]]*3+[xyz[d.free_nodes]])
    geometry['grid_shape_zyx']=np.array(d.shape)
    return context(self,*args,**kwargs)
class Captured(BaseException):pass
def capture(self,A,b):
    assert self.operator_key is None and self.factor is None
    A=A.tocsr();assert A.shape==(239745,239745) and len(b)==A.shape[0]
    assert geometry['coordinates_zyx'].shape==(A.shape[0],3)
    assert np.all(np.isfinite(A.data)) and np.all(np.isfinite(b))
    fixture=out/'first_DC_matrix.npz'
    np.savez_compressed(fixture,data=A.data,indices=A.indices,indptr=A.indptr,shape=A.shape,b=b,**geometry)
    profile.emit('first_DC_matrix_captured',dimension=A.shape[0],nnz=int(A.nnz))
    (out/'capture.json').write_text(json.dumps(dict(status='captured_before_first_DC_factorization',
        fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),shape=list(A.shape),nnz=int(A.nnz),
        seconds=time.monotonic()-start,new_simulation_steps=0,new_physics_credit=0),indent=2)+'\n')
    raise Captured()
dielectric.DielectricSheetDriftDiffusion._linear_context=observe_geometry
linear._ReusedGMRES.solve=capture
sys.argv=[str(w/'input/independent_y2_probe.py'),'thermionic','space','3','128','probe',str(out/'not_a_completed_probe')]
try:runpy.run_path(sys.argv[0],run_name='__main__')
except Captured:pass
else:raise AssertionError('Expected capture before any linear solve')
