"""Actual vector Sentaurus GLK: nonuniform 2D FE/linear dielectric composite."""
from functools import lru_cache
import json
from pathlib import Path
import numpy as np
import pytest
from scipy.interpolate import RegularGridInterpolator
from tcad.core import PyDeviceSimulator

DATA=Path(__file__).parent/'data/sentaurus_multidimensional_fe.json'


@lru_cache(maxsize=6)
def native(cells,times):
    h=.8e-6/cells;x=np.r_[0.,(np.arange(cells)+.5)*h,.8e-6]
    y=(np.arange(cells)+.5)*h;nx=len(x);n=nx*cells
    xx=np.tile(x,cells);yy=np.repeat(y,nx)
    mask=(xx<.4e-6)&(yy<.4e-6);eps=8.8542e-12*np.where(mask,15.,3.9)
    zero=np.zeros(n);left=xx==0;right=xx==.8e-6
    sim=PyDeviceSimulator(nx,cells,1,h,h,1e-6)
    sim.set_x_positions(x);sim.set_y_positions(y)
    sim.set_permittivity(eps);sim.set_mobility(zero,zero);sim.set_doping(zero)
    sim.set_effective_dos(np.full(n,1e16),np.full(n,1e16));sim.set_bandgap(np.full(n,6.))
    sim.set_recombination(np.full(n,1e100),np.full(n,1e100))
    sim.set_dirichlet_potential({int(i):0. for i in np.flatnonzero(left|right)})
    sim.set_initial_guess(zero,zero,zero)
    sim.set_ferroelectric_enabled(True);sim.set_ferroelectric_model(0)
    sim.set_ferroelectric_params(mask.astype(np.int8),1e8,1e12)
    sim.set_ferroelectric_gamma(.1);sim.set_ferroelectric_polar_axis(0)
    sim.set_transient_lk_coupled(True);sim.set_transient_lk_material_field(True)
    sim.set_gummel_max_iter(80);sim.set_tolerance(1e-12)
    sim.set_transient_dt(times[-1]);sim.set_transient_t_final(times[-1])
    voltage=np.interp(times,[0.,2e-10,6e-10],[0.,.02,.02])
    sim.set_transient_voltage_waveforms(np.array(times),{int(i):voltage for i in np.flatnonzero(left)})
    states=sim.solve_transient();assert all(s['valid'] for s in states)
    np.testing.assert_array_equal([s['time_s'] for s in states],times)
    points=np.array([[.2,.2],[.2,.6],[.6,.2],[.6,.6]])*1e-6
    def sample(values,where=points):
        return RegularGridInterpolator((y,x),values.reshape(cells,nx))(where[:,::-1])
    values={k:[] for k in ['phi','ex','ey','px','py','charge','current']}
    for s in states:
        for key,field in [('phi','phi'),('ex','Ex'),('ey','Ey')]:values[key].append(sample(s[field]))
        p=s['P'].reshape(n,3)
        for axis,key in enumerate(['px','py']):values[key].append(sample(p[:,axis],points[:1]))
        # The left plane sorts first in the terminal ledger.
        values['charge'].append(s['electrode_charges_C'])
        values['current'].append(s['electrode_total_currents_A'] if s['time_s']>0 else np.zeros(2))
    return {k:np.asarray(v) for k,v in values.items()}


def errors(actual,case,keys=('phi','ex','ey','px','py','charge','current')):
    result={}
    for key in keys:
        reference=np.array(case['reference'][key]);scale=np.max(abs(reference))
        assert scale>0
        result[key]=float(np.max(abs(actual[key]-reference))/scale)
    return result


@pytest.mark.parametrize('index',[0,1])
def test_actual_vector_sentaurus_composite(index):
    data=json.loads(DATA.read_text());case=data['cases'][index]
    actual=native(data['accepted_native_cells'],tuple(case['times_s']))
    assert max(errors(actual,case).values())<data['relative_budget']
    assert np.max(abs(actual['charge'].sum(axis=1)))<np.max(abs(actual['charge']))*1e-8
    assert np.max(abs(actual['current'].sum(axis=1)))<np.max(abs(actual['current']))*1e-8


def test_vector_reference_has_transverse_response():
    data=json.loads(DATA.read_text())
    for case in data['cases']:
        ref=case['reference']
        assert np.max(abs(np.array(ref['py'])))>1e-7
        assert np.max(abs(np.array(ref['ey'])))>100
        assert not data['physical_validated']


def test_commercial_vector_reference_mesh_refinement():
    data=json.loads(DATA.read_text());coarse,fine=data['cases']
    assert coarse['times_s']==fine['times_s']
    actual={k:np.asarray(v) for k,v in coarse['reference'].items()}
    assert max(errors(actual,fine).values())<data['reference_budget']


def test_transverse_polarization_cannot_hide_behind_larger_axial_component():
    data=json.loads(DATA.read_text());case=data['cases'][-1]
    actual={k:np.asarray(v) for k,v in case['reference'].items()}
    actual['py']=actual['py']*1.2
    assert errors(actual,case)['py']>data['relative_budget']
