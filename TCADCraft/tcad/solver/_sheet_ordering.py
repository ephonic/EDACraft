"""Geometry-only nested dissection and immutable symmetric LU permutations."""
from dataclasses import dataclass
import hashlib

import numpy as np


def _geometric_nd_permutation(coordinates, leaf_size=64):
    coordinates=np.asarray(coordinates)
    if (coordinates.ndim!=2 or coordinates.shape[1]!=3 or not len(coordinates)
            or not np.all(np.isfinite(coordinates))):
        raise ValueError('geometric ordering requires finite nonempty N by 3 coordinates')
    if not isinstance(leaf_size,int) or isinstance(leaf_size,bool) or leaf_size<1:
        raise ValueError('leaf_size must be a positive integer')
    chunks=[]
    def visit(indices):
        if len(indices)<=leaf_size:
            chunks.append(indices);return
        points=coordinates[indices];best=None
        for axis in range(3):
            values=np.unique(points[:,axis]);middle=len(values)//2
            for value in values[max(1,middle-1):min(len(values)-1,middle+2)]:
                left=points[:,axis]<value;right=points[:,axis]>value
                nl,nr=int(left.sum()),int(right.sum());ns=len(indices)-nl-nr
                if not min(nl,nr):continue
                cost=ns*(len(indices)/(2*min(nl,nr)))**2
                if best is None or cost<best[0]:best=(cost,left,right)
        if best is None:
            chunks.append(indices);return
        _,left,right=best
        visit(indices[left]);visit(indices[right]);chunks.append(indices[~(left|right)])
    visit(np.arange(len(coordinates)))
    return np.concatenate(chunks)


@dataclass(frozen=True, eq=False, init=False)
class _SymmetricPermutation:
    indices: np.ndarray
    key: str

    def __init__(self, indices):
        p=np.asarray(indices)
        if (p.ndim!=1 or not p.size or p.dtype.kind not in 'iu'
                or not np.array_equal(np.sort(p),np.arange(p.size))):
            raise ValueError('permutation must contain each integer index exactly once')
        # A bytes owner prevents callers from re-enabling the write flag.
        raw=np.asarray(p,dtype='<i8').tobytes()
        object.__setattr__(self,'indices',np.frombuffer(raw,dtype='<i8'))
        object.__setattr__(self,'key',hashlib.sha256(raw).hexdigest())

    def __deepcopy__(self, memo):
        memo[id(self)]=self
        return self


class _PermutedLU:
    def __init__(self, factor, permutation):
        self.factor=factor
        self.permutation=permutation

    def solve(self, b):
        p=self.permutation.indices
        solution=self.factor.solve(b[p])
        result=np.empty_like(solution)
        result[p]=solution
        return result
