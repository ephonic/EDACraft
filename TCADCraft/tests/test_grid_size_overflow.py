"""Reject native dimension wrap before allocation; retain empty/count semantics."""
import itertools
import json
import struct
import sys
import numpy as np
import pytest
from tcad.core import PyDeviceSimulator

BITS=8*struct.calcsize('P')
LIMIT=(1<<BITS)-1
HIGH=1<<(BITS-1)
BAD=sorted({dims for seed in [(HIGH,2,1),(HIGH+1,2,1),(LIMIT,LIMIT,1),(1<<(BITS-2),4,1),(1<<(BITS//2),1<<(BITS//4),1<<(BITS-BITS//2-BITS//4))] for dims in itertools.permutations(seed)})
GOOD=[(0,1,1),(1,0,1),(1,1,0),(1,1,1),(2,1,1),(1,3,2),(3,3,3)]

@pytest.mark.parametrize('dims',BAD)
def test_overflow_rejects_and_existing_object_survives(dims):
    assert np.prod(dims,dtype=object)>LIMIT
    control=PyDeviceSimulator(3,1,1,1e-8,1.,1.)
    before=np.asarray(control.get_permittivity()).copy()
    with pytest.raises(OverflowError,match='grid node count overflows size_t'):
        PyDeviceSimulator(*dims,1e-8,1.,1.)
    np.testing.assert_array_equal(control.get_permittivity(),before)
    assert control.npts==3
    retry=PyDeviceSimulator(2,1,1,1e-8,1.,1.)
    assert retry.npts==2

@pytest.mark.parametrize('dims',GOOD)
def test_representable_small_counts(dims):
    sim=PyDeviceSimulator(*dims,1e-8,1.,1.)
    assert sim.npts==int(np.prod(dims,dtype=object))
    assert (sim.nx,sim.ny,sim.nz)==dims
    assert len(sim.get_permittivity())==sim.npts

if __name__=='__main__':
    rows=[]
    for dims in BAD+GOOD:
        product=int(np.prod(dims,dtype=object))
        assert product<=LIMIT or (product&LIMIT)<=8  # keep parent observation bounded
        try:
            sim=PyDeviceSimulator(*dims,1e-8,1.,1.)
            rows.append(dict(dims=dims,rejected=False,count=sim.npts))
        except OverflowError as error:
            rows.append(dict(dims=dims,rejected=True,error=str(error)))
    with open(sys.argv[1],'w',encoding='utf8') as output:json.dump(rows,output,indent=2)
