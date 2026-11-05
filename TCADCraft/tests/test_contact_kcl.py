"""Internal reservoirs permit current jumps; free carrier equations still hold."""
import numpy as np
import pytest
from tcad.core import PyDeviceSimulator, native_constants

H=1e-7
VT=.02585
CASES=[('classical',a,g,l,c,f,b) for a in range(3) for g in [False,True]
       for l in [False,True] for c in [1,2,3] for f in range(3) for b in [False,True]]
CASES += [('quantum',a,g,l,3,f,b) for a in range(3) for g in [False,True]
          for l in [False,True] for f in range(3) for b in [False,True]]


def mobility(left,right,spacing,hole,hfs,policy,contact):
    mu=.05 if hole else .1
    if hfs==2 and (policy or not contact):
        ratio=mu*VT*abs(np.log(right/left))/spacing/(4e4 if hole else 5e4)
        if ratio>1e-12:mu/=1+ratio if hole else np.sqrt(1+ratio*ratio)
    return mu


def profile(pos,contacts,hole,hfs,policy):
    values=[1.2e19 if hole else 2e19]
    rate=values[0]*(.05 if hole else .1)*VT/H*(.03 if hole else .05)
    for i,h in enumerate(np.diff(pos)):
        if i and i in contacts:rate*=.6 if hole else 1.7
        low,high=values[-1],values[-1]*4
        contact=i in contacts or i+1 in contacts
        for _ in range(60):
            mid=(low+high)/2
            flux=mobility(values[-1],mid,h,hole,hfs,policy,contact)*VT*(mid-values[-1])/h
            if flux<rate:low=mid
            else:high=mid
        values.append((low+high)/2)
    return np.asarray(values)


def make_case(kind,axis,graded,logs,layout,hfs,policy):
    pos=H*np.array([0,1,2.3,3.8,5,6.5,8] if graded else range(7),dtype=float)
    shape=[1,1,1];shape[axis]=7
    sim=PyDeviceSimulator(*shape,H,H,H)
    if graded:getattr(sim,'set_'+'xyz'[axis]+'_positions')(np.ascontiguousarray(pos))
    nb={0,6}|({3} if layout in (1,3) else set())
    pb={0,6}|({3} if layout in (2,3) else set())
    if kind=='quantum':
        n=np.full(7,2e19);p=n.copy()
        phi=.04*np.where(pos<=pos[3],pos/pos[3],(pos[-1]-pos)/(pos[-1]-pos[3]))
        potential={i:phi[i] for i in [0,3,6]}
        sim.set_quantum_enabled(True);sim.set_density_gradient_coefficients(1e-15,7e-16)
    else:
        n=profile(pos,nb,False,hfs,policy);p=profile(pos,pb,True,hfs,policy)
        phi=np.zeros(7);potential={0:0.,6:0.}
    doping=n-p
    sim.set_mobility(np.full(7,.1),np.full(7,.05));sim.set_doping(doping)
    sim.set_permittivity(np.full(7,11.7*8.854187817e-12))
    sim.set_effective_dos(np.full(7,1e19),np.full(7,1e19));sim.set_bandgap(np.full(7,6.))
    sim.set_recombination(np.full(7,1e100),np.full(7,1e100));sim.set_thermal_voltage(VT)
    sim.set_dirichlet_potential(potential)
    sim.set_electron_bc({i:n[i] for i in nb});sim.set_hole_bc({i:p[i] for i in pb})
    sim.set_high_field_saturation(hfs>0,5e4,4e4,2.,1.,1 if hfs==1 else 0)
    sim.set_hfs_quasi_fermi_at_contacts(policy)
    sim.set_initial_guess(phi,n,p);sim.set_use_newton(True);sim.set_newton_primary(True)
    sim.set_newton_use_log_space(logs);sim.set_gummel_max_iter(1)
    return sim,dict(kind=kind,axis=axis,pos=pos,n=n,p=p,doping=doping,potential=potential,nb=nb,pb=pb,hfs=hfs,policy=policy)


def independent_balance(r,c):
    phi,n,p=(np.asarray(r[k]) for k in ('phi','n','p'))
    assert np.all(np.isfinite(np.r_[phi,n,p])) and min(np.min(n),np.min(p))>0
    pos=c['pos'];q=float(native_constants()['elementary_charge_C']);eps=11.7*8.854187817e-12
    for i in range(7):
        if i in c['potential']:assert abs(phi[i]-c['potential'][i])/VT<1e-10
        else:
            width=(pos[i+1]-pos[i-1])/2;left=eps/width/(pos[i]-pos[i-1]);right=eps/width/(pos[i+1]-pos[i])
            rhs=q*(p[i]-n[i]+c['doping'][i]);applied=left*(phi[i]-phi[i-1])+right*(phi[i]-phi[i+1])
            scale=2*VT*(left+right)+q*(n[i]+p[i]+abs(c['doping'][i]))+abs(rhs)
            assert abs(applied-rhs)/scale<1e-10
    currents=[]
    for hole,carrier,contacts,coefficient in [(False,n,c['nb'],1e-15),(True,p,c['pb'],7e-16)]:
        correction=np.zeros(7)
        if c['kind']=='quantum':
            u=np.sqrt(carrier)
            correction[1:-1]=np.clip(coefficient*2/(pos[2:]-pos[:-2])*np.diff(np.diff(u)/np.diff(pos))/u[1:-1],-4*VT,4*VT)
            for i in contacts:correction[i]=0
            np.testing.assert_allclose(r['Qp' if hole else 'Qn'],correction,rtol=2e-10,atol=2e-14)
        transport=phi+(-1 if hole else 1)*correction
        delta=np.diff(transport)/VT
        def bernoulli(x):
            result=1-x/2+x*x/12
            active=abs(x)>1e-5;result[active]=x[active]/np.expm1(x[active]);return result
        bp,bm=bernoulli(delta),bernoulli(-delta)
        force=abs(np.diff(transport))/np.diff(pos)
        if c['hfs']==2:
            force=abs(np.diff(transport)+(1 if hole else -1)*VT*np.diff(np.log(carrier)))/np.diff(pos)
            if not c['policy']:
                for i in range(6):
                    if i in contacts or i+1 in contacts:force[i]=abs(transport[i+1]-transport[i])/(pos[i+1]-pos[i])
        mu=.05 if hole else .1
        diffusion=np.full(6,mu*VT)/np.diff(pos)
        if c['hfs']:
            ratio=mu*force/(4e4 if hole else 5e4)
            diffusion/=1+ratio if hole else np.sqrt(1+ratio*ratio)
        current=q*diffusion*(carrier[:-1]*bp-carrier[1:]*bm if hole else carrier[1:]*bp-carrier[:-1]*bm)
        np.testing.assert_allclose(r[('Jp_' if hole else 'Jn_')+'xyz'[c['axis']]][:-1],current,rtol=2e-10,atol=2e-8)
        for i in range(7):
            if i in contacts:np.testing.assert_allclose(carrier[i],c['p' if hole else 'n'][i],rtol=1e-12,atol=0.)
            elif 0<i<6:
                # Includes the unconstrained species at another species' contact.
                assert abs(current[i]-current[i-1])/max(1.,abs(current[i]),abs(current[i-1]))<1e-9
        currents.append(current)
    total=sum(currents);cuts=sorted(c['nb']|c['pb'])
    for a,b in zip(cuts[:-1],cuts[1:]):
        values=total[a:b];assert np.ptp(values)/max(1.,np.max(abs(values)))<1e-9
    assert np.ptp(total)/max(1.,np.max(abs(total)))>.01
    audit=r['steady_equation_audit'];assert audit['available'] and audit['equations_pass']
    assert max(audit[k] for k in ['poisson_scaled_linf','electron_backward_error_linf','hole_backward_error_linf'])<1e-10
    assert not audit['physical_validated'] and not audit['complete_device_energy']


@pytest.mark.parametrize('kind,axis,graded,logs,layout,hfs,policy',CASES)
def test_internal_reservoir_public_success(kind,axis,graded,logs,layout,hfs,policy):
    sim,case=make_case(kind,axis,graded,logs,layout,hfs,policy)
    result=sim.solve(audit_newton=True)
    assert result['converged']
    independent_balance(result,case)
