"""Independent material half-edge energy closure on actual 2-D/3-D native states.

This is a fixed-grid, charge-free, local componentwise LK check. Field energy
uses each half material's E**2, rather than the square of the nodal mean E.
"""
import numpy as np
import pytest


def quadrature(states,shape,faces):
    xyz=np.array([(i,j,k) for k in range(shape[2])
        for j in range(shape[1]) for i in range(shape[0])])
    spacing=[1e-8,1.3e-8,1.7e-8]
    # Match the actual float64 mesh supplied to the native solver exactly.
    axes=[(np.arange(n,dtype=float)**1.3*h).astype(np.longdouble)
        for n,h in zip(shape,spacing)]
    eps=(8.854187817e-12*(10+.4*xyz.sum(axis=1))).astype(np.longdouble)
    phi=np.array([s['phi'] for s in states],dtype=np.longdouble)
    p=np.array([s['P'].reshape(-1,3) for s in states],dtype=np.longdouble)
    widths=[]
    for a,(n,h,x) in enumerate(zip(shape,spacing,axes)):
        if n==1:widths.append(np.array([h],dtype=np.longdouble));continue
        edge=np.diff(x);w=(np.r_[0.,edge]+np.r_[edge,0.])/2
        if 'xXyYzZ'[2*a] in faces:w[0]+=edge[0]/2
        if 'xXyYzZ'[2*a+1] in faces:w[-1]+=edge[-1]/2
        widths.append(w)
    volume=np.prod([w[xyz[:,a]] for a,w in enumerate(widths)],axis=0)
    fields=[];weights=[];dielectrics=[]
    strides=[1,shape[0],shape[0]*shape[1]]
    for i,coord in enumerate(xyz):
        for a in range(3):
            area=volume[i]/widths[a][coord[a]]
            if coord[a]+1<shape[a]:
                j=i+strides[a];h=axes[a][coord[a]+1]-axes[a][coord[a]]
                e=2*eps[i]*eps[j]/(eps[i]+eps[j])
                d=e*((phi[:,i]-phi[:,j])/h+(p[:,i,a]/eps[i]+p[:,j,a]/eps[j])/2)
                for q in (i,j):
                    fields.append((d-p[:,q,a])/eps[q]);weights.append(h*area/2);dielectrics.append(eps[q])
            for side in (0,1):
                if ('xXyYzZ'[2*a+side] in faces and
                        coord[a]==(shape[a]-1 if side else 0)):
                    h=axes[a][-1]-axes[a][-2] if side else axes[a][1]-axes[a][0]
                    fields.append(-p[:,i,a]/eps[i]);weights.append(h*area/2);dielectrics.append(eps[i])
    return p,volume,np.array(fields).T,np.array(weights),np.array(dielectrics),eps


@pytest.mark.parametrize('shape',[(4,3,1),(4,1,3),(1,4,3),(3,3,3)])
@pytest.mark.parametrize('partial',[False,True])
def test_material_half_edge_global_backward_euler_energy(shape,partial):
    from test_lk_material_multidimensional import device
    drive=next(a for a,n in enumerate(shape) if n>1)
    faces=''.join('xXyYzZ'[2*a:2*a+2] for a,n in enumerate(shape) if n>1 and a!=drive)
    sim,spec=device(shape,partial,0,natural_faces=faces)
    sim.set_ferroelectric_builtin_field(0.);sim.set_ferroelectric_depol(0.)
    states=sim.solve_transient();assert all(s['valid'] for s in states)
    p,volume,e,w,eps,node_eps=quadrature(states,shape,faces)
    dt=np.diff(np.array([s['time_s'] for s in states],dtype=np.longdouble))
    v=np.array([s['electrode_voltages_V'] for s in states],dtype=np.longdouble)
    q=np.array([s['electrode_charges_C'] for s in states],dtype=np.longdouble)
    dp=np.diff(p,axis=0);de=np.diff(e,axis=0);old=p[:-1];new=p[1:]
    a=np.longdouble('-1e8');b=np.longdouble('1e12');gamma=np.longdouble('.1')
    source=np.sum(v[1:]*np.diff(q,axis=0),axis=1)
    dielectric=np.sum(w*eps*de*(e[1:]+e[:-1])/2,axis=1)
    dielectric_be=np.sum(w*eps*de*de/2,axis=1)
    landau=np.sum(volume[None,:,None]*dp*(a*(new+old)/2+
        b*(new+old)*(new*new+old*old)/4),axis=(1,2))
    loss=np.sum(volume[None,:,None]*gamma*dp*dp/dt[:,None,None],axis=(1,2))
    landau_be=np.sum(volume[None,:,None]*dp*dp*(a/2+
        b*(3*new*new+2*new*old+old*old)/4),axis=(1,2))
    residual=source-dielectric-dielectric_be-landau-loss-landau_be
    # Fixed external scale: a large cancelling source/storage term cannot
    # inflate this budget. Also check local LK through the native ledger.
    assert np.max(abs(residual))<np.longdouble('1e-28')
    assert np.max(abs(np.sum(q,axis=1)))<np.longdouble('1e-25')
    from tcad.postprocess.lk_energy import audit_transient_lk_energy
    assert audit_transient_lk_energy(states)['valid']
    # An apparently reasonable nodal-mean-E energy drops subcell variance.
    means=np.array([np.column_stack([s['Ex'],s['Ey'],s['Ez']]) for s in states],dtype=np.longdouble)
    dm=np.diff(means,axis=0)
    wrong=np.sum(volume[None,:,None]*node_eps[None,:,None]*
        (dm*(means[1:]+means[:-1])/2+dm*dm/2),axis=(1,2))
    wrong_residual=source-wrong-landau-loss-landau_be
    # Nearly uniform all-FE controls need not discriminate quadratures. The
    # mixed FE/oxide controls must reject the missing subcell variance.
    if partial:assert np.max(abs(wrong_residual))>np.longdouble('1e-26')
