"""Independent full vector LK/Poisson block solve on 2-D and 3-D grids."""
import numpy as np
import pytest
from scipy.optimize import root
from tcad.core import PyDeviceSimulator

SHAPES=[(4,3,1),(4,1,3),(1,4,3),(3,3,3)]
EPS0=8.854187817e-12


def device(shape,partial,polar_axis,charged=False,natural_faces=''):
    count=int(np.prod(shape));xyz=np.array([(i,j,k) for k in range(shape[2])
        for j in range(shape[1]) for i in range(shape[0])])
    spacing=[1e-8,1.3e-8,1.7e-8]
    axes=[np.arange(n,dtype=float)**1.3*h for n,h in zip(shape,spacing)]
    drive=next(a for a,n in enumerate(shape) if n>1)
    contacts=(xyz[:,drive]==0)|(xyz[:,drive]==shape[drive]-1)
    boundary=np.where(xyz[:,drive]==0,0.,.08)
    eps=EPS0*(10+.4*xyz.sum(axis=1))
    mask=((xyz.sum(axis=1)%3!=0) if partial else np.ones(count,dtype=bool))
    sim=PyDeviceSimulator(*shape,*spacing)
    for setter,x in zip([sim.set_x_positions,sim.set_y_positions,sim.set_z_positions],axes):setter(x)
    zero=np.zeros(count)
    doping=np.where(contacts,0.,1e23*(1+.1*xyz.sum(axis=1))) if charged else zero
    sim.set_permittivity(eps);sim.set_mobility(zero,zero);sim.set_doping(doping)
    sim.set_effective_dos(np.full(count,1e16),np.full(count,1e16));sim.set_bandgap(np.full(count,6.))
    sim.set_recombination(np.full(count,1e100),np.full(count,1e100))
    sim.set_dirichlet_potential({int(i):float(boundary[i]) for i in np.flatnonzero(contacts)})
    sim.set_initial_guess(zero,zero,zero)
    sim.set_ferroelectric_enabled(True);sim.set_ferroelectric_model(0)
    sim.set_ferroelectric_params(mask.astype(np.int8),-1e8,1e12)
    sim.set_ferroelectric_gamma(.1);sim.set_ferroelectric_polar_axis(polar_axis)
    sim.set_ferroelectric_builtin_field(2e5);sim.set_ferroelectric_depol(30.)
    sim.set_transient_lk_coupled(True);sim.set_transient_lk_material_field(True)
    sim.set_transient_lk_zero_d_faces(natural_faces)
    sim.set_transient_dt(1e-10);sim.set_transient_t_final(2.1e-10)
    sim.set_gummel_max_iter(80);sim.set_tolerance(1e-12)
    widths=[];support=[]
    for a,(n,h,x) in enumerate(zip(shape,spacing,axes)):
        if n==1:widths.append(np.array([h]));support.append(np.zeros(1));continue
        dx=np.diff(x);support.append((np.r_[0.,dx]+np.r_[dx,0.])/2)
        if 'xXyYzZ'[2*a] in natural_faces:support[-1][0]+=dx[0]/2
        if 'xXyYzZ'[2*a+1] in natural_faces:support[-1][-1]+=dx[-1]/2
        widths.append((np.r_[dx[0],dx]+np.r_[dx,dx[-1]])/2)
    volume=np.prod([w[xyz[:,a]] for a,w in enumerate(widths)],axis=0)
    edges=[];strides=[1,shape[0],shape[0]*shape[1]]
    for i,coord in enumerate(xyz):
        for a in range(3):
            if coord[a]+1>=shape[a]:continue
            j=i+strides[a];h=axes[a][coord[a]+1]-axes[a][coord[a]]
            area=volume[i]/widths[a][coord[a]]
            edges.append((i,j,a,h,area,2*eps[i]*eps[j]/(eps[i]+eps[j])))
    def fields(phi,p):
        field=np.zeros((count,3));div=np.zeros(count);ports=np.zeros(2)
        for i,j,a,h,area,e in edges:
            d=e*((phi[i]-phi[j])/h+(p[i,a]/eps[i]+p[j,a]/eps[j])/2)
            div[i]+=area*d;div[j]-=area*d
            field[i,a]+=h*(d-p[i,a])/(2*support[a][xyz[i,a]]*eps[i])
            field[j,a]+=h*(d-p[j,a])/(2*support[a][xyz[j,a]]*eps[j])
            if contacts[i] and not contacts[j]:ports[0]+=area*d
            if not contacts[i] and contacts[j]:ports[1]-=area*d
        for a,x in enumerate(axes):
            for side in (0,1):
                if 'xXyYzZ'[2*a+side] not in natural_faces:continue
                at=xyz[:,a]==(shape[a]-1 if side else 0)
                length=(x[-1]-x[-2] if side else x[1]-x[0])/2
                field[at,a]-=length*p[at,a]/(support[a][xyz[at,a]]*eps[at])
        return field,div/volume,ports
    return sim,dict(count=count,contacts=contacts,boundary=boundary,mask=mask,
        fields=fields,polar_axis=polar_axis,doping=doping,volume=volume)


def independent_step(spec,previous,phi,dt):
    n=spec['count'];mask=spec['mask'];contacts=spec['contacts'];axis=spec['polar_axis']
    def equations(x):
        phi=x[:n];p=x[n:].reshape(n,3)
        field,div,_=spec['fields'](phi,p)
        fp=(div-1.602176634e-19*spec['doping'])*1e-7
        fp[contacts]=phi[contacts]-spec['boundary'][contacts]
        f=-1e8*p+1e12*p**3+.1/dt*(p-previous)-field
        f[:,axis]+=2e5+p[:,axis]/(30*EPS0)
        f/=1e9;f[~mask]=p[~mask]
        return np.r_[fp,f.ravel()]
    solved=root(equations,np.r_[phi,previous.ravel()],tol=1e-11)
    assert max(abs(equations(solved.x)))<1e-10,solved.message
    return solved.x[:n],solved.x[n:].reshape(n,3)


@pytest.mark.parametrize('shape',SHAPES)
@pytest.mark.parametrize('partial',[False,True])
@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('charged',[False,True])
def test_multidimensional_material_response_matches_full_block(shape,partial,axis,charged):
    sim,spec=device(shape,partial,axis,charged);states=sim.solve_transient()
    old=np.zeros((spec['count'],3));phi=states[0]['phi']
    for s in states[1:]:
        assert s['valid'] and s['lk_coupled'] and s['lk_material_field']
        phi,old=independent_step(spec,old,phi,s['dt_s'])
        np.testing.assert_allclose(s['phi'],phi,rtol=1e-8,atol=1e-11)
        np.testing.assert_allclose(s['P'].reshape(-1,3),old,rtol=1e-8,atol=1e-12)
        field,div,ports=spec['fields'](phi,old)
        np.testing.assert_allclose(np.column_stack([s['Ex'],s['Ey'],s['Ez']]),field,rtol=2e-8,atol=2e-4)
        residual=div-1.602176634e-19*spec['doping']
        assert max(abs(residual[~spec['contacts']]))<1e-7
        assert s['electrode_charge_available']
        np.testing.assert_allclose(s['electrode_charges_C'],ports,rtol=1e-8,atol=1e-28)
        enclosed=1.602176634e-19*np.dot(spec['doping'],spec['volume'])
        assert abs(sum(ports)+enclosed)<max(abs(ports))*1e-8


def test_multidimensional_material_failure_rolls_back_and_retry_matches_fresh():
    sim,spec=device((4,3,1),True,1);sim.set_gummel_max_iter(0)
    failed=sim.solve_transient();assert not failed[-1]['valid']
    for key in ['phi','n','p','P']:np.testing.assert_array_equal(failed[0][key],failed[-1][key])
    sim.set_gummel_max_iter(80);retry=sim.solve_transient()
    fresh,_=device((4,3,1),True,1);direct=fresh.solve_transient()
    for s,t in zip(retry,direct):
        for key in ['phi','n','p','P']:np.testing.assert_array_equal(s[key],t[key])
