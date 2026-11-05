"""Independent 2-D PB/SG/BE controls and material-selective PB initialization."""
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest
from scipy.sparse import coo_matrix,diags
from scipy.sparse.linalg import spsolve

from tcad.core import PyDeviceSimulator
from tcad.validation import audit_electrode_charge_balance
from test_transient_mixed_volumes import bernoulli

QE=1.602176634e-19
VT=300*8.617333262145e-5
NI=1.07500384888443e16
POINTS=[(7.5,15.),(30.,15.),(52.5,15.),(7.5,45.),(30.,45.),(52.5,45.)]


def equilibrium(spec):
    """Independent sparse Newton solve of finite-volume Poisson-Boltzmann."""
    m=spec['matrix'];free=spec['free'];volume=spec['volume'];mobile=spec['mobile']
    phi=np.zeros(len(volume));ni=spec['ni']
    for _ in range(40):
        n=mobile*ni*np.exp(phi/VT);p=mobile*ni*np.exp(-phi/VT)
        residual=m@phi-QE*volume*(p-n+spec['doping'])
        # Double sparse matvec roundoff is about 5e-13 on the 32-cell mesh;
        # this remains 10000 times tighter than the independent state audit.
        if max(abs(residual[free]))<1e-12*QE*ni*max(volume):break
        jac=m+diags(QE*volume*(n+p)/VT)
        step=spsolve(jac[free][:,free],-residual[free])
        phi[free]+=step*min(1.,VT/max(abs(step)))
    else:raise AssertionError('independent PB failed')
    return phi,n,p


def mobile_device(cells=8,sign=1,axis=0,log_space=False,*,ni=NI,times=None,voltage=None,
                  initialization='masked',oxide_dos_zero=False,carrier_contacts=True):
    trans=(axis+1)%3;shape=[1,1,1];shape[axis]=cells+1;shape[trans]=cells//2
    h=60e-6/cells;spacing=[1e-6]*3;spacing[axis]=h;spacing[trans]=2*h
    axes=[np.array([0.]) for _ in range(3)];axes[axis]=np.linspace(0,60e-6,cells+1)
    axes[trans]=(np.arange(cells//2)+.5)*2*h
    xyz=np.array([(i,j,k) for k in range(shape[2]) for j in range(shape[1]) for i in range(shape[0])])
    size=len(xyz);x=axes[axis][xyz[:,axis]];y=axes[trans][xyz[:,trans]]
    mobile=y<30e-6;lower=xyz[:,axis]==0;upper=xyz[:,axis]==cells;contacts=lower|upper
    eps=8.8542e-12*np.where(mobile,11.7,15.)
    overlap=np.maximum(0.,np.minimum(x+h/2,45e-6)-np.maximum(x-h/2,15e-6))/h
    doping=sign*1e17*overlap*(~mobile)
    volume=np.full(size,np.prod(spacing));strides=[1,shape[0],shape[0]*shape[1]]
    edges=[]
    for i,coord in enumerate(xyz):
     for d in range(3):
        if coord[d]+1>=shape[d]:continue
        j=i+strides[d];distance=axes[d][coord[d]+1]-axes[d][coord[d]]
        area=np.prod([spacing[e] for e in range(3) if e!=d]);face=2*eps[i]*eps[j]/(eps[i]+eps[j])
        edges.append((i,j,distance,area,face))
    a,b,distance,area,face=np.array(edges).T;a=a.astype(int);b=b.astype(int);weights=face*area/distance
    matrix=coo_matrix((np.r_[weights,weights,-weights,-weights],
        (np.r_[a,b,a,b],np.r_[a,b,b,a])),shape=(size,size)).tocsr()
    if times is None:times=np.array([0.,.5e-6,2e-6,3e-6]);voltage=np.array([0.,.0025,.01,.01])
    spec=dict(matrix=matrix,free=np.flatnonzero(~contacts),volume=volume,doping=doping,
        mobile=mobile,contacts=contacts,lower=lower,upper=upper,ni=ni,shape=shape,axes=axes,
        axis=axis,trans=trans,a=a,b=b,distance=distance,area=area,weights=weights,
        times=np.array(times),voltage=np.array(voltage),mu_n=.1*mobile,mu_p=.05*mobile)
    reference=equilibrium(spec);spec['equilibrium']=reference
    sim=PyDeviceSimulator(*shape,*spacing)
    for values,setter in zip(axes,[sim.set_x_positions,sim.set_y_positions,sim.set_z_positions]):setter(values)
    sim.set_permittivity(eps);sim.set_mobility(spec['mu_n'],spec['mu_p']);sim.set_doping(doping)
    dos=np.where(mobile,ni,0.) if oxide_dos_zero else np.full(size,ni)
    sim.set_effective_dos(dos,dos);sim.set_bandgap(np.zeros(size));sim.set_thermal_voltage(VT)
    sim.set_recombination(np.full(size,1e100),np.full(size,1e100))
    sim.set_dirichlet_potential({int(i):0. for i in np.flatnonzero(contacts)})
    if initialization=='independent':sim.set_initial_guess(*reference)
    elif initialization=='legacy':spec['native_equilibrium']=sim.solve_equilibrium(tolerance=1e-12)
    else:spec['native_equilibrium']=sim.solve_equilibrium(tolerance=1e-12,carrier_mask=mobile)
    density=ni*mobile
    if carrier_contacts:
        sim.set_electron_bc({int(i):float(density[i]) for i in np.flatnonzero(contacts)})
        sim.set_hole_bc({int(i):float(density[i]) for i in np.flatnonzero(contacts)})
    sim.set_transient_voltage_waveforms(times,{int(i):voltage for i in np.flatnonzero(lower)})
    sim.set_newton_use_log_space(log_space);sim.set_gummel_max_iter(80);sim.set_tolerance(1e-12)
    sim.set_transient_dt(float(times[-1]));sim.set_transient_t_final(float(times[-1]))
    return sim,spec


def graph_audit(states,spec):
    a,b=spec['a'],spec['b'];contacts=spec['contacts'];free=spec['free']
    left=spec['lower'][a]&~contacts[b];right=~contacts[a]&spec['upper'][b]
    def ports(flux):return np.array([sum(flux[left]),-sum(flux[right])])
    charges=[];enclosed=[];gauss=[];kcl=[];residual=[]
    for k,s in enumerate(states):
        assert s['valid'] and s['electrode_charge_available'] and s['charge_ledger_available']
        n,p,phi=s['n'],s['p'],s['phi']
        poisson=spec['matrix']@phi-QE*spec['volume']*(p-n+spec['doping'])
        assert max(abs(poisson[free]))/(QE*spec['ni']*max(spec['volume']))<1e-8
        q=ports(-spec['weights']*(phi[b]-phi[a]))
        np.testing.assert_allclose(s['electrode_charges_C'],q,rtol=2e-10,atol=1e-32)
        enclosed.append(QE*np.dot((p-n+spec['doping'])[free],spec['volume'][free]))
        charges.append(q)
        assert not s['dielectric_energy_available']
        if not k:continue
        old=states[k-1];dt=s['dt_s'];u=(phi[b]-phi[a])/VT;bp,bm=bernoulli(u),bernoulli(-u)
        rates=[]
        for mu,density,first,second in [(spec['mu_n'],n,bm,bp),(spec['mu_p'],p,bp,bm)]:
            den=mu[a]+mu[b];face=np.divide(2*mu[a]*mu[b],den,out=np.zeros_like(den),where=den>0)
            rates.append(face*VT*spec['area']/spec['distance']*(density[a]*first-density[b]*second))
        conduction=ports(QE*(-rates[0]+rates[1]));delta=phi-old['phi']
        displacement=ports(-spec['weights']*(delta[b]-delta[a]))/dt
        scale=max(max(abs(conduction)),max(abs(displacement)))
        assert s['total_terminal_current_available']
        for name,value in [('conduction',conduction),('displacement',displacement),('total',conduction+displacement)]:
            assert max(abs(s['electrode_'+name+'_currents_A']-value))/scale<1e-8
        kcl.append(abs(sum(conduction+displacement))/scale)
        assert kcl[-1]<1e-7
        active=free[spec['mobile'][free]]
        for name,rate in zip(['n','p'],rates):
            f=(s[name]-old[name])*spec['volume']/dt
            np.add.at(f,a,rate);np.add.at(f,b,-rate)
            err=max(abs(f[active]))/(spec['ni']*max(spec['volume'])/dt)
            residual.append(err);assert err<2e-7
    enclosed=np.array(enclosed);charges=np.array(charges)
    audit=audit_electrode_charge_balance([s['time_s'] for s in states],charges,enclosed,
        boundary_coverage_complete=True,converged=True,charge_scale_C=max(abs(enclosed)),
        charge_atol_C=0.,charge_rtol=1e-8)
    assert audit['charge_balance_compatible']
    return dict(gauss_error=audit['max_abs_charge_balance_residual_C']/max(abs(enclosed)),
        kcl_error=max(kcl),continuity_error=max(residual))


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('sign',[1,-1])
@pytest.mark.parametrize('zero_dos',[False,True])
def test_masked_pb_retains_fixed_charge_and_exactly_empty_insulator(axis,sign,zero_dos):
    sim,spec=mobile_device(sign=sign,axis=axis,oxide_dos_zero=zero_dos)
    r=spec['native_equilibrium'];assert r['converged']
    for key,expected in zip(['phi','n','p'],spec['equilibrium']):
        np.testing.assert_allclose(r[key],expected,rtol=2e-10,atol=1e-14 if key=='phi' else 0.)
    np.testing.assert_array_equal(r['n'][~spec['mobile']],0.)
    np.testing.assert_array_equal(r['p'][~spec['mobile']],0.)
    # The fixed charge remains in the oxide even though its mobile mask is off.
    assert max(abs(r['phi'][~spec['mobile']]))>.02
    graph_audit(sim.solve_transient(),spec)


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('sign',[1,-1])
@pytest.mark.parametrize('log_space',[False,True])
def test_mobile_mixed_pb_handoff_satisfies_independent_gauss_sg_be(axis,sign,log_space):
    sim,spec=mobile_device(sign=sign,axis=axis,log_space=log_space)
    states=sim.solve_transient();graph_audit(states,spec)
    assert max(abs(states[-1]['n']-states[0]['n']))>.001*spec['ni']
    altered=deepcopy(states);altered[-1]['electrode_total_currents_A'][0]*=1.2
    with pytest.raises(AssertionError):graph_audit(altered,spec)


@pytest.mark.parametrize('bad',[True,[],[True],np.ones(36),np.full(36,np.nan),[[True]*36],['x']*36])
def test_pb_carrier_mask_rejects_nonboolean_or_wrong_shape(bad):
    sim,spec=mobile_device(initialization='independent')
    with pytest.raises(ValueError):sim.solve_equilibrium(carrier_mask=bad)


@pytest.mark.parametrize('axis',[0,1,2])
def test_all_true_mask_preserves_legacy_pb_and_mask_does_not_persist(axis):
    sim,spec=mobile_device(axis=axis,initialization='independent',carrier_contacts=False)
    default=sim.solve_equilibrium()
    explicit=sim.solve_equilibrium(carrier_mask=np.ones(len(spec['mobile']),dtype=bool))
    for key in ['phi','n','p','residual_history','update_history_V','damping_history']:
        np.testing.assert_array_equal(default[key],explicit[key])
    mask=spec['mobile'].copy();masked=sim.solve_equilibrium(carrier_mask=mask)
    assert masked['converged'];mask[:]=False
    repeated=sim.solve_equilibrium()
    for key in ['phi','n','p']:np.testing.assert_array_equal(repeated[key],default[key])


@pytest.mark.parametrize('sign',[1,-1])
def test_empty_pb_carrier_selection_keeps_fixed_electrostatic_charge(sign):
    sim,spec=mobile_device(sign=sign,initialization='independent',oxide_dos_zero=True,carrier_contacts=False)
    r=sim.solve_equilibrium(carrier_mask=np.zeros(len(spec['mobile']),dtype=bool))
    assert r['converged'];np.testing.assert_array_equal(r['n'],0.);np.testing.assert_array_equal(r['p'],0.)
    f=spec['matrix']@r['phi']-QE*spec['volume']*spec['doping']
    assert max(abs(f[spec['free']]))/(QE*spec['ni']*max(spec['volume']))<1e-10


@pytest.mark.parametrize('kind',['zero_budget','invalid_mask','incompatible_reservoir'])
def test_failed_material_pb_initialization_preserves_previous_seed(kind):
    sim,spec=mobile_device();accepted=spec['native_equilibrium']
    if kind=='zero_budget':
        r=sim.solve_equilibrium(max_iter=0,carrier_mask=spec['mobile'])
        assert not r['converged'] and not r['initial_guess_committed']
    elif kind=='invalid_mask':
        with pytest.raises(ValueError):sim.solve_equilibrium(carrier_mask=[1]*len(spec['mobile']))
    else:
        with pytest.raises(ValueError):sim.solve_equilibrium(carrier_mask=np.zeros(len(spec['mobile']),dtype=bool))
    sim.set_transient_t_final(0.)
    state,=sim.solve_transient()
    for key in ['phi','n','p']:np.testing.assert_allclose(state[key],accepted[key],rtol=2e-13,atol=1e-20)


def fixture():return json.loads((Path(__file__).parent/'data/sentaurus_mobile_space_charge_2d.json').read_text())


def commercial_errors(states,spec,case):
    from scipy.interpolate import RegularGridInterpolator
    def sample(s,key):
        values=np.asarray(s[key]).reshape(spec['shape'][::-1]).transpose(2,1,0)
        values=np.moveaxis(values,[spec['axis'],spec['trans']],[0,1]).reshape(len(spec['axes'][spec['axis']]),-1)
        return RegularGridInterpolator((spec['axes'][spec['axis']],spec['axes'][spec['trans']]),values)(np.array(POINTS)*1e-6)
    raw=case['raw'];actual={};expected={}
    for name,key,suffix,factor in [('phi','phi','ElectrostaticPotential',1.),
            ('Eaxis',['Ex','Ey','Ez'][spec['axis']],'ElectricField/x',100.),
            ('Etransverse',['Ex','Ey','Ez'][spec['trans']],'ElectricField/y',100.),
            ('n','n','eDensity',1e6),('p','p','hDensity',1e6)]:
        count=3 if name in ['n','p'] else 6
        actual[name]=np.array([sample(s,key)[:count] for s in states])
        expected[name]=factor*np.column_stack([raw[f'Pos({x:g},{y:g}) {suffix}'] for x,y in POINTS[:count]])
    actual['charge']=np.array([s['electrode_charges_C'] for s in states]);expected['charge']=np.array(case['surface_charges_C'])
    for name,label in [('total','TotalCurrent'),('displacement','DisplacementCurrent'),('conduction',None)]:
        actual[name]=np.array([s['electrode_'+name+'_currents_A'] for s in states[1:]])
        expected[name]=np.column_stack([raw[p+' '+label][1:] if label else
            np.array(raw[p+' eCurrent'][1:])+raw[p+' hCurrent'][1:] for p in ['left','right']])
    return {k:float(np.max(abs(actual[k]-expected[k]))/np.max(abs(expected[k]))) for k in actual}


@pytest.mark.parametrize('index',[2,3])
def test_actual_sentaurus_mobile_space_charge_2d(index):
    c=fixture()['cases'][index];r=c['raw'];ni=np.sqrt(r['Pos(0,15) eDensity'][0]*r['Pos(0,15) hDensity'][0])*1e6
    sim,spec=mobile_device(24,c['sign'],ni=ni,times=r['time'],voltage=r['left OuterVoltage'])
    states=sim.solve_transient();graph_audit(states,spec)
    assert max(commercial_errors(states,spec,c).values())<.03


@pytest.mark.parametrize('index',range(4))
def test_actual_mobile_charge_reference_requires_physical_surface_flux(index):
    c=fixture()['cases'][index];enclosed=np.array(c['enclosed_charge_C'])
    opts=dict(boundary_coverage_complete=True,converged=True,charge_scale_C=max(abs(enclosed)),
        charge_atol_C=0.,charge_rtol=.02)
    accepted=audit_electrode_charge_balance(c['raw']['time'],c['surface_charges_C'],enclosed,**opts)
    rejected=audit_electrode_charge_balance(c['raw']['time'],c['raw_charges_C'],enclosed,**opts)
    assert accepted['charge_balance_compatible'] and not rejected['charge_balance_compatible']
    assert rejected['max_abs_charge_balance_residual_C']/max(abs(enclosed))>.99
    assert max(abs(np.array(c['mobile_charge_C'])))/abs(c['nominal_charge_C'])>.1
    assert np.ptp(c['mobile_charge_C'])>1e-21
    assert max(abs(np.array(c['fixed_charge_C'])-c['nominal_charge_C']))/abs(c['nominal_charge_C'])<.02


@pytest.mark.parametrize('sign',[1,-1])
def test_actual_mobile_charge_mesh_refines_dose_and_surface_gauss(sign):
    cases=[c for c in fixture()['cases'] if c['sign']==sign]
    dose=[max(abs(np.array(c['fixed_charge_C'])-c['nominal_charge_C']))/abs(c['nominal_charge_C']) for c in cases]
    assert [c['commercial_cells'] for c in cases]==[128,256]
    assert dose[1]<dose[0] and dose[1]<.004


@pytest.mark.parametrize('tamper',['raw_charge','drop_mobile_charge'])
def test_mobile_reference_rejects_missing_or_replaced_physical_charge(tamper):
    c=fixture()['cases'][2];enclosed=c['enclosed_charge_C'];charge=c['surface_charges_C']
    if tamper=='raw_charge':charge=c['raw_charges_C']
    else:enclosed=c['fixed_charge_C']
    result=audit_electrode_charge_balance(c['raw']['time'],charge,enclosed,
        boundary_coverage_complete=True,converged=True,charge_scale_C=max(abs(np.array(enclosed))),
        charge_atol_C=0.,charge_rtol=.02)
    assert not result['charge_balance_compatible']
