"""Exercise the integrated public linear context, without a prototype monkeypatch."""
from pathlib import Path
import json,resource,sys,time
import numpy as np
from scipy.sparse import csr_matrix
from tcad.solver._sheet_linear import _ReusedGMRES
from tcad.solver._sheet_ordering import _geometric_nd_permutation, _SymmetricPermutation
fixture=Path(sys.argv[1]);out=Path(sys.argv[2])
with np.load(fixture,allow_pickle=False) as f:
    A=csr_matrix((f['data'],f['indices'],f['indptr']),shape=tuple(f['shape']));b=f['b'];coords=f['coordinates_zyx']
t=time.monotonic();p=_SymmetricPermutation(_geometric_nd_permutation(coords));ordering_s=time.monotonic()-t
context=_ReusedGMRES(None,1e-12,ordering='GEOMETRIC_ND',permutation=p)
t=time.monotonic();x=context.solve(A,b);elapsed=time.monotonic()-t
residual=float(np.max(abs(A@x-b)))
assert np.all(np.isfinite(x)) and residual<=1e-14
assert context.diagnostics()['factor_ordering']=='GEOMETRIC_ND'
np.savez_compressed(out.with_suffix('.solution.npz'),x=x,permutation=p.indices)
result=dict(status='passed_integrated_GEOMETRIC_ND_original_true_residual_guard',
    ordering_s=ordering_s,solve_wall_s=elapsed,peak_rss_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
    true_scaled_residual_linf=residual,diagnostics=context.diagnostics(),new_simulation_steps=0,full_device_qualification=False)
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
