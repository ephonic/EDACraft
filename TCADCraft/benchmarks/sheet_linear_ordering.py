"""Measure one LU ordering on a captured sheet Newton system in a fresh process.

Run separately for each ordering so peak RSS and factorization memory are not
inherited from an earlier factor. This is a linear-system benchmark, not a
whole-device or full-trajectory qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import resource
import time

import numpy as np
from scipy.sparse import csr_matrix

from tcad.solver._sheet_linear import _ReusedGMRES


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ordering',choices=('COLAMD','MMD_AT_PLUS_A'),required=True)
    p.add_argument('--fixture',type=Path,default=Path(__file__).resolve().parents[1]/'tests/data/sheet_phase2_linear_system.npz')
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    with np.load(args.fixture,allow_pickle=False) as f:
        A=csr_matrix((f['data'],f['indices'],f['indptr']),shape=tuple(f['shape']))
        b=f['b'].copy()
    context=_ReusedGMRES(None,1e-12,ordering=args.ordering)
    start=time.monotonic();x=context.solve(A,b);seconds=time.monotonic()-start
    residual=float(np.max(abs(A@x-b)))
    assert np.all(np.isfinite(x)) and residual<=1e-14
    lu=context.factor.factor
    # macOS reports ru_maxrss in bytes; Linux reports KiB.
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024**2 if platform.system()=='Darwin' else 1024)
    result=dict(ordering=args.ordering,fixture_sha256=hashlib.sha256(args.fixture.read_bytes()).hexdigest(),
                shape=list(A.shape),nnz_A=int(A.nnz),nnz_L=int(lu.L.nnz),nnz_U=int(lu.U.nnz),
                seconds=seconds,peak_rss_MiB=rss,true_scaled_residual_linf=residual,
                diagnostics=context.diagnostics(),full_device_qualification=False)
    text=json.dumps(result,indent=2)+'\n'
    if args.output is not None:args.output.write_text(text,encoding='utf-8')
    print(text,end='')


if __name__=='__main__':main()
