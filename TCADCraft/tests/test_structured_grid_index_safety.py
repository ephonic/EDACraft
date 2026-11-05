"""Public indexing must not wrap, truncate, or alias another mesh node."""
import json
import sys
import warnings
import numpy as np
import pytest
from tcad.mesh.structured_grid import StructuredGrid

BOX=((0.,1.),)*3
TYPES=[int,np.int8,np.uint8,np.int16,np.uint16,np.int32,np.uint32,np.int64,np.uint64]
INVALID=[True,False,np.bool_(True),np.bool_(False),1.,np.float64(1.),float('nan'),float('inf'),1.2,'1',None,1+0j,[1],np.array([1])]
BOUNDS=[(axis,value) for axis,count in enumerate((3,4,5)) for value in (-1,count,count+1,-10**100,10**100,np.uint64(2**64-1))]

class IndexLike:
    def __init__(self,value):self.value=value
    def __index__(self):return self.value

@pytest.mark.parametrize('dtype',TYPES)
def test_narrow_dimensions_and_all_nodes(dtype):
    grid=StructuredGrid(BOX,*[dtype(7)]*3)
    assert grid.npts()==343 and type(grid.npts()) is int
    assert all(type(value) is int for value in grid.shape())
    for flat in range(343):
        expected=tuple(int(v) for v in np.unravel_index(flat,(7,7,7),order='F'))
        typed_flat=dtype(flat) if dtype is not int and flat<=np.iinfo(dtype).max else flat
        assert grid.ijk(typed_flat)==expected
        actual=grid.index(*[dtype(v) for v in expected])
        assert type(actual) is int and actual==flat
        np.testing.assert_allclose(grid.node_coords[actual],np.array(expected)/6,rtol=0,atol=2e-16)

@pytest.mark.parametrize('axis,value',BOUNDS)
def test_coordinate_bounds_do_not_alias(axis,value):
    grid=StructuredGrid(BOX,3,4,5);before=grid.node_coords.copy();coords=[0,0,0];coords[axis]=value
    with pytest.raises(IndexError,match='outside the grid'):grid.index(*coords)
    np.testing.assert_array_equal(grid.node_coords,before)
    assert grid.index(2,3,4)==59 and grid.ijk(59)==(2,3,4)

@pytest.mark.parametrize('value',[-1,60,61,-10**100,10**100,np.int64(-1),np.uint64(2**64-1)])
def test_flat_bounds(value):
    grid=StructuredGrid(BOX,3,4,5)
    with pytest.raises(IndexError,match='outside the grid'):grid.ijk(value)

@pytest.mark.parametrize('axis',range(3))
@pytest.mark.parametrize('value',INVALID)
def test_coordinate_types(axis,value):
    grid=StructuredGrid(BOX,3,4,5);coords=[0,0,0];coords[axis]=value
    with pytest.raises(TypeError,match='integer index'):grid.index(*coords)

@pytest.mark.parametrize('value',INVALID)
def test_flat_types(value):
    grid=StructuredGrid(BOX,3,4,5)
    with pytest.raises(TypeError,match='integer index'):grid.ijk(value)

@pytest.mark.parametrize('shape',[(1,1,1),(1,3,5),(3,1,5),(3,4,1),(3,4,5)])
def test_integer_protocol_and_independent_order(shape):
    grid=StructuredGrid(BOX,*shape)
    for flat in range(int(np.prod(shape))):
        coords=tuple(int(v) for v in np.unravel_index(flat,shape,order='F'))
        assert grid.ijk(IndexLike(flat))==coords
        assert grid.index(*[IndexLike(v) for v in coords])==int(np.ravel_multi_index(coords,shape,order='F'))

def observe():
    records=[]
    for dtype in TYPES:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',RuntimeWarning)
            grid=StructuredGrid(BOX,*[dtype(7)]*3)
            records.append(dict(kind='dimensions',dtype=dtype.__name__,npts=int(grid.npts()),last_index=int(grid.index(6,6,6)),expected=343))
    grid=StructuredGrid(BOX,3,4,5)
    fixtures=[('coordinate',axis,value) for axis,value in BOUNDS]+[('flat',-1,value) for value in [-1,60,61,-10**100,10**100,np.int64(-1),np.uint64(2**64-1)]]
    fixtures += [('coordinate_type',axis,value) for axis in range(3) for value in INVALID]+[('flat_type',-1,value) for value in INVALID]
    for kind,axis,value in fixtures:
        expected='IndexError' if kind in ['coordinate','flat'] else 'TypeError';error=None
        try:
            if kind.startswith('coordinate'):
                coords=[0,0,0];coords[axis]=value;grid.index(*coords)
            else:grid.ijk(value)
        except Exception as caught:error=type(caught).__name__
        records.append(dict(kind=kind,axis=axis,input_type=type(value).__name__,input=repr(value),error=error,expected_error=expected,passed=error==expected))
    return records

if __name__=='__main__':
    with open(sys.argv[1],'w',encoding='utf8') as out:json.dump(observe(),out,indent=2)
