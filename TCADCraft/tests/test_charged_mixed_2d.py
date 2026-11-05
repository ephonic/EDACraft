"""Localized fixed charge: independent 2-D graph and actual commercial fields."""
import json
from pathlib import Path
from copy import deepcopy

import numpy as np
import pytest
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

from tcad.core import PyDeviceSimulator
from tcad.validation import audit_electrode_charge_balance

QE=1.602176634e-19
EPS0=8.8542e-12
POINTS=[(.075,.15),(.3,.15),(.525,.15),(.075,.45),(.3,.45),(.525,.45)]


def charged_device(cells,sign,axis=0,log_space=False,times=None,voltage=None):
    transverse=(axis+1)%3;shape=[1,1,1];shape[axis]=cells+1;shape[transverse]=cells//2
    h=.6e-6/cells;spacing=[1e-6]*3;spacing[axis]=h;spacing[transverse]=2*h
    axes=[np.array([0.])]*3;axes[axis]=np.linspace(0,.6e-6,cells+1)
    axes[transverse]=(np.arange(cells//2)+.5)*2*h
    widths=[np.full(n,spacing[d]) for d,n in enumerate(shape)]
    coords=np.array([(i,j,k) for k in range(shape[2]) for j in range(shape[1]) for i in range(shape[0])])
    size=len(coords);x=axes[axis][coords[:,axis]];y=axes[transverse][coords[:,transverse]]
    eps=EPS0*np.where(y>.3e-6,15.,3.9)
    # Physical charge patch is integrated over each control volume, including
    # its two x interfaces. Boundary contact rows carry no enclosed charge.
    overlap=np.maximum(0.,np.minimum(x+h/2,.45e-6)-np.maximum(x-h/2,.15e-6))/h
    doping=sign*1e21*overlap*(y>.3e-6)
    lower=coords[:,axis]==0;upper=coords[:,axis]==cells;contacts=lower|upper
    volume=np.prod(np.column_stack([widths[d][coords[:,d]] for d in range(3)]),axis=1)
    strides=[1,shape[0],shape[0]*shape[1]];a=[];b=[];weights=[]
    for idx,xyz in enumerate(coords):
     for d in range(3):
        if xyz[d]+1>=shape[d]:continue
        other=idx+strides[d]
        face=2*eps[idx]*eps[other]/(eps[idx]+eps[other])
        area=np.prod([widths[e][xyz[e]] for e in range(3) if e!=d])
        a.append(idx);b.append(other);weights.append(face*area/(axes[d][xyz[d]+1]-axes[d][xyz[d]]))
    a=np.array(a);b=np.array(b);weights=np.array(weights)
    matrix=coo_matrix((np.r_[weights,weights,-weights,-weights],
        (np.r_[a,b,a,b],np.r_[a,b,b,a])),shape=(size,size)).tocsr()
    free=np.flatnonzero(~contacts);fixed=np.flatnonzero(contacts)
    source=np.zeros(size);source[free]=spsolve(matrix[free][:,free],QE*doping[free]*volume[free])
    unit=lower.astype(float)
    unit[free]=spsolve(matrix[free][:,free],-matrix[free][:,fixed]@unit[fixed])
    if times is None:times=np.array([0.,2e-10,1e-9]);voltage=np.array([0.,.01,.01])
    sim=PyDeviceSimulator(*shape,*spacing)
    for values,setter in zip(axes,[sim.set_x_positions,sim.set_y_positions,sim.set_z_positions]):setter(values)
    sim.set_permittivity(eps);sim.set_mobility(np.zeros(size),np.zeros(size));sim.set_doping(doping)
    sim.set_effective_dos(np.full(size,1e16),np.full(size,1e16));sim.set_bandgap(np.full(size,6.))
    sim.set_recombination(np.full(size,1e100),np.full(size,1e100))
    sim.set_initial_guess(np.zeros(size),np.zeros(size),np.zeros(size))
    sim.set_dirichlet_potential({int(i):0. for i in fixed})
    sim.set_transient_voltage_waveforms(times,{int(i):voltage for i in np.flatnonzero(lower)})
    sim.set_newton_use_log_space(log_space);sim.set_gummel_max_iter(80);sim.set_tolerance(1e-12)
    sim.set_transient_dt(float(times[-1]));sim.set_transient_t_final(float(times[-1]))
    return sim,dict(a=a,b=b,weights=weights,source=source,unit=unit,lower=lower,upper=upper,
        contacts=contacts,enclosed=float(QE*np.dot(doping[free],volume[free])),
        shape=shape,axis=axis,transverse=transverse,axes=axes,x=x,y=y,
        times=np.array(times),voltage=np.array(voltage))


def check_graph(states,spec):
    a,b,w=spec['a'],spec['b'],spec['weights'];contacts=spec['contacts']
    left=spec['lower'][a]&~contacts[b];right=~contacts[a]&spec['upper'][b]
    def ports(phi):
        flux=-w*(phi[b]-phi[a]);return np.array([flux[left].sum(),-flux[right].sum()])
    errors=[];charges=[]
    for k,state in enumerate(states):
        assert state['valid'] and state['electrode_charge_available']
        v=np.interp(state['time_s'],spec['times'],spec['voltage'])
        reference=spec['source']+v*spec['unit']
        np.testing.assert_allclose(state['phi'],reference,rtol=2e-10,atol=1e-13)
        q=ports(reference);charges.append(state['electrode_charges_C'])
        np.testing.assert_allclose(charges[-1],q,rtol=2e-10,atol=1e-33)
        assert not state['dielectric_energy_available']
        if k:
            assert state['total_terminal_current_available']
            previous_v=np.interp(states[k-1]['time_s'],spec['times'],spec['voltage'])
            expected=ports((v-previous_v)*spec['unit'])/state['dt_s']
            scale=max(abs(ports(.01*spec['unit'])/2e-10))
            errors.append(float(max(abs(state['electrode_total_currents_A']-expected))/scale))
            assert errors[-1]<2e-9
            np.testing.assert_array_equal(state['electrode_conduction_currents_A'],0.)
    audit=audit_electrode_charge_balance([s['time_s'] for s in states],charges,
        np.full(len(states),spec['enclosed']),boundary_coverage_complete=True,converged=True,
        charge_scale_C=abs(spec['enclosed']),charge_atol_C=0.,charge_rtol=1e-8)
    assert audit['charge_balance_compatible']
    return dict(gauss_error=audit['max_abs_charge_balance_residual_C']/abs(spec['enclosed']),
        current_error=max(errors))


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('sign',[1,-1])
@pytest.mark.parametrize('log_space',[False,True])
def test_localized_fixed_charge_uses_full_multidimensional_poisson(axis,sign,log_space):
    sim,spec=charged_device(8,sign,axis,log_space);states=sim.solve_transient()
    check_graph(states,spec)
    altered=deepcopy(states);altered[-1]['electrode_charges_C'][0]*=1.05
    with pytest.raises(AssertionError):check_graph(altered,spec)


def sample(state,spec,key):
    from scipy.interpolate import RegularGridInterpolator
    shape=spec['shape'];axis=spec['axis'];transverse=spec['transverse']
    values=np.asarray(state[key]).reshape(shape[::-1]).transpose(2,1,0)
    values=np.moveaxis(values,[axis,transverse],[0,1]).reshape(shape[axis],shape[transverse])
    return RegularGridInterpolator((spec['axes'][axis],spec['axes'][transverse]),values)(np.array(POINTS)*1e-6)


def commercial_errors(states,spec,case):
    raw=case['raw'];actual={};expected={}
    for key in ['phi','Eaxis','Etransverse']:
        native_key={'phi':'phi','Eaxis':['Ex','Ey','Ez'][spec['axis']],
            'Etransverse':['Ex','Ey','Ez'][spec['transverse']]}[key]
        actual[key]=np.array([sample(s,spec,native_key) for s in states])
        suffix={'phi':'ElectrostaticPotential','Eaxis':'ElectricField/x','Etransverse':'ElectricField/y'}[key]
        expected[key]=np.column_stack([raw[f'Pos({x:g},{y:g}) {suffix}'] for x,y in POINTS])
        if key!='phi':expected[key]*=100.
    actual['charge']=np.array([s['electrode_charges_C'] for s in states]);expected['charge']=np.array(case['surface_charges_C'])
    actual['current']=np.array([s['electrode_total_currents_A'] for s in states[1:]])
    expected['current']=np.column_stack([raw[n+' TotalCurrent'][1:] for n in ['left','right']])
    # All probes of a field share its global peak scale, including zero local
    # symmetry components. Static space charge cannot mask current errors.
    return {k:float(np.max(np.abs(actual[k]-expected[k]))/np.max(np.abs(expected[k]))) for k in actual}


def cases():return json.loads((Path(__file__).parent/'data/sentaurus_charged_mixed_2d.json').read_text())['cases']


@pytest.mark.parametrize('index',[2,3])
@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('log_space',[False,True])
def test_actual_sentaurus_localized_charge_fields_and_currents(index,axis,log_space):
    case=cases()[index];raw=case['raw']
    assert case['commercial_cells']==256
    # The 16-cell rotated control meets the same fixed budget. The separately
    # archived analysis also replays both meshes, including all 32-cell states.
    sim,spec=charged_device(16,case['sign'],axis,log_space,raw['time'],raw['left OuterVoltage'])
    states=sim.solve_transient();check_graph(states,spec)
    assert max(commercial_errors(states,spec,case).values())<=.02


def reference_gate(case,charges):
    return audit_electrode_charge_balance(case['raw']['time'],charges,case['enclosed_charge_C'],
        boundary_coverage_complete=True,converged=True,charge_scale_C=max(abs(np.array(case['enclosed_charge_C']))),
        charge_atol_C=0.,charge_rtol=.02)


@pytest.mark.parametrize('index',range(4))
def test_commercial_field_flux_and_raw_charge_are_audited_separately(index):
    c=cases()[index]
    assert reference_gate(c,c['surface_charges_C'])['charge_balance_compatible']
    assert not reference_gate(c,c['raw_charges_C'])['charge_balance_compatible']
    assert np.max(np.abs(np.array(c['enclosed_charge_C'])-c['nominal_charge_C']))/abs(c['nominal_charge_C'])<.02


@pytest.mark.parametrize('sign',[1,-1])
def test_actual_fixed_charge_dose_and_surface_residual_decrease_with_mesh(sign):
    selected=sorted([c for c in cases() if c['sign']==sign],key=lambda c:c['commercial_cells'])
    assert [c['commercial_cells'] for c in selected]==[128,256]
    dose=[max(abs(np.array(c['enclosed_charge_C'])-c['nominal_charge_C'])) for c in selected]
    gauss=[reference_gate(c,c['surface_charges_C'])['max_abs_charge_balance_residual_C'] for c in selected]
    assert dose[1]<.6*dose[0] and gauss[1]<.6*gauss[0]


@pytest.mark.parametrize('index',[2,3])
@pytest.mark.parametrize('defect',['raw_substitution','surface_20_percent'])
def test_fixed_charge_reference_rejects_raw_substitution_and_surface_corruption(index,defect):
    c=cases()[index]
    q=np.array(c['raw_charges_C'] if defect=='raw_substitution' else c['surface_charges_C'])
    if defect=='surface_20_percent':q[-1,0]*=1.2
    assert not reference_gate(c,q)['charge_balance_compatible']
