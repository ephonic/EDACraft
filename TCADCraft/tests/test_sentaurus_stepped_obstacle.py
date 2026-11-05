"""Stepped intrinsic Si channel: actual commercial fields, densities and current."""
from functools import lru_cache
import json
from pathlib import Path
import numpy as np
import pytest
from scipy.interpolate import RegularGridInterpolator
from tcad.core import PyDeviceSimulator
from test_transient_mixed_volumes import bernoulli

DATA=Path(__file__).parent/'data/sentaurus_stepped_obstacle.json'
QE=1.602176634e-19
POINTS=[(7.5,7.5),(30,7.5),(52.5,7.5),(30,45)]


@lru_cache(maxsize=3)
def native(cells,ni):
    h=60e-6/cells;x=np.r_[0.,(np.arange(cells)+.5)*h,60e-6]
    y=(np.arange(cells//2)+.5)*2*h;nx=len(x);ny=len(y);n=nx*ny
    xx=np.tile(x,ny);yy=np.repeat(y,nx)
    height=np.where((xx>15e-6)&(xx<45e-6),15e-6,45e-6)
    mobile=yy<height;eps=8.8542e-12*np.where(mobile,11.7,15.)
    left=xx==0;right=xx==60e-6;contacts=left|right
    sim=PyDeviceSimulator(nx,ny,1,h,2*h,1e-6)
    sim.set_x_positions(x);sim.set_y_positions(y)
    sim.set_permittivity(eps);sim.set_mobility(.1*mobile,.05*mobile)
    sim.set_doping(np.zeros(n));sim.set_effective_dos(np.full(n,ni),np.full(n,ni))
    sim.set_bandgap(np.zeros(n));sim.set_thermal_voltage(300*8.617333262145e-5)
    sim.set_recombination(np.full(n,1e100),np.full(n,1e100))
    sim.set_dirichlet_potential({int(i):(.01 if left[i] else 0.) for i in np.flatnonzero(contacts)})
    density=ni*mobile
    sim.set_electron_bc({int(i):float(density[i]) for i in np.flatnonzero(contacts)})
    sim.set_hole_bc({int(i):float(density[i]) for i in np.flatnonzero(contacts)})
    sim.set_initial_guess(.01*(1-xx/60e-6),density,density)
    sim.set_use_newton(True);sim.set_newton_primary(True)
    sim.set_gummel_max_iter(80);sim.set_tolerance(1e-12)
    state=sim.solve();assert state['converged']
    # Independent graph integration; no material-clipped terminal area.
    edges=[]
    dx=np.diff(x);width=(np.r_[dx[0],dx]+np.r_[dx,dx[-1]])/2
    volume=np.tile(width,ny)*2*h*1e-6
    for j in range(ny):
        for i in range(nx):
            a=i+nx*j
            if i+1<nx:edges.append((a,a+1,dx[i],2*h*1e-6))
            if j+1<ny:edges.append((a,a+nx,2*h,width[i]*1e-6))
    a,b,distance,area=np.array(edges).T;a=a.astype(int);b=b.astype(int)
    field=(state['phi'][a]-state['phi'][b])/distance
    d=2*eps[a]*eps[b]/(eps[a]+eps[b])*field*area
    poisson=np.zeros(n);np.add.at(poisson,a,d);np.add.at(poisson,b,-d)
    poisson-=QE*volume*(state['p']-state['n'])
    assert max(abs(poisson[~contacts]))<1e-8*max(abs(d))
    currents=[];divs=[]
    u=(state['phi'][b]-state['phi'][a])/(300*8.617333262145e-5)
    for key,mu,sign in [('n',.1,-1),('p',.05,1)]:
        first,second=(bernoulli(-u),bernoulli(u)) if key=='n' else (bernoulli(u),bernoulli(-u))
        rate=mu*(mobile[a]&mobile[b])*(300*8.617333262145e-5)*area/distance*(state[key][a]*first-state[key][b]*second)
        div=np.zeros(n);np.add.at(div,a,rate);np.add.at(div,b,-rate)
        assert max(abs(div[~contacts]))<1e-7*max(abs(rate))
        currents.append(sign*QE*rate);divs.append(div)
    total=sum(currents);l=left[a]&~contacts[b];r=~contacts[a]&right[b]
    port=np.array([sum(total[l]),-sum(total[r])])
    assert abs(sum(port))<max(abs(port))*1e-8
    def sample(values,points=POINTS):
        return RegularGridInterpolator((y,x),values.reshape(ny,nx))(np.array(points)[:,::-1]*1e-6)
    return dict(phi=sample(state['phi']),ex=sample(state['Ex']),ey=sample(state['Ey']),
        n=sample(state['n'],POINTS[:3]),p=sample(state['p'],POINTS[:3]),current=port,
        kcl_error=float(abs(sum(port))/max(abs(port))),
        poisson_relative=float(max(abs(poisson[~contacts]))/max(abs(d))))


def errors(actual,case):
    expected=case['reference'];result={}
    for key in ['phi','ex','ey','n','p','current']:
        ref=np.array(expected[key]);scale=max(abs(ref))
        result[key]=float(max(abs(actual[key]-ref))/scale)
    return result


@pytest.mark.parametrize('index',[0,1])
def test_actual_sentaurus_stepped_channel(index):
    data=json.loads(DATA.read_text());c=data['cases'][index]
    actual=native(data['accepted_native_cells'],data['ni_m3'])
    assert max(errors(actual,c).values())<data['relative_budget']


def test_stepped_reference_mesh_convergence():
    data=json.loads(DATA.read_text());a,b=data['cases']
    assert max(errors({k:np.array(v) for k,v in a['reference'].items()},b).values())<data['mesh_reference_budget']
