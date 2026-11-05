"""Conservative sheet DD: manufactured solutions, Jacobian and circuit ledgers."""
import itertools
import numpy as np
import pytest
from tcad.material import graphene_sheet,mos2_sheet,mos2_channel
from tcad.material.sheet import Q
from tcad.solver.sheet_drift_diffusion import SheetDriftDiffusion


def material(kind):
    return graphene_sheet() if kind=='graphene' else mos2_sheet(reference_eV=-.9)


def device(kind='graphene',nx=9,ny=5,nonuniform=False,width=2e-6,multiplier=1.):
    x=np.linspace(0.,1.,nx)**(1.3 if nonuniform else 1.)*1e-6
    y=np.linspace(0.,1.,ny)**(1.2 if nonuniform else 1.)*width
    mat=material(kind);st=mat.statistics();dop=float(st.n_m2-st.p_m2)
    return SheetDriftDiffusion(x,y,mat,gate_capacitance_F_m2=.02,
        mobility_n_m2_Vs=.02*multiplier,mobility_p_m2_Vs=.01*multiplier,
        sheet_permittivity_F=4e-20,doping_m2=dop)


def ledgers(result):
    assert result['converged'],(result['status'],result['residual_scaled_linf'])
    currents=result['terminal_currents_into_sheet_A'];scale=max(map(abs,currents.values()))
    assert abs(result['terminal_current_sum_A'])<1e-8*scale+1e-25
    assert abs(result['terminal_power_W']-result['dissipation_W'])<1e-7*result['dissipation_W']+1e-27
    assert result['dissipation_W']>=0
    charge_scale=abs(result['gate_charge_C'])+abs(result['sheet_charge_C'])+sum(map(abs,result['contact_charge_C'].values()))
    assert abs(result['gauss_charge_sum_C'])<1e-8*charge_scale+1e-28
    assert np.all(result['n_m2']>=0) and np.all(result['p_m2']>=0)


@pytest.mark.parametrize('kind,nonuniform,drain',itertools.product(('graphene','mos2'),(False,True),(-.02,0.,.02)))
def test_manufactured_uniform_carriers_ohms_law_and_newton(kind,nonuniform,drain):
    sim=device(kind,nonuniform=nonuniform);phi=np.broadcast_to(drain*sim.x/sim.x[-1],sim.shape)
    st=sim.material.statistics();rho=float(st.charge_C_m2)+Q*sim.doping.reshape(sim.shape)
    gate=phi-rho/sim.cap.reshape(sim.shape)
    bump=np.sin(np.pi*sim.x/sim.x[-1])[None,:]*np.ones(sim.shape)
    initial=dict(phi_V=phi+.03*bump,Fn_eV=-phi+.01*bump,Fp_eV=-phi-.01*bump)
    result=sim.solve(gate_voltage_V=gate,drain_voltage_V=drain,initial=initial)
    ledgers(result);assert result['iterations']>0
    np.testing.assert_allclose(result['phi_V'],phi,atol=1e-10,rtol=0)
    np.testing.assert_allclose(result['Fn_eV'],-phi,atol=1e-10,rtol=0)
    np.testing.assert_allclose(result['Fp_eV'],-phi,atol=1e-10,rtol=0)
    expected=Q*(sim.mu_n*float(st.n_m2)+sim.mu_p*float(st.p_m2))*(sim.y[-1]-sim.y[0])/(sim.x[-1]-sim.x[0])*drain
    assert result['terminal_currents_into_sheet_A']['drain']==pytest.approx(expected,rel=2e-8,abs=1e-22)


@pytest.mark.parametrize('kind',['graphene','mos2'])
def test_full_analytic_jacobian_against_directional_difference(kind):
    sim=device(kind,nx=5,ny=3,nonuniform=True);N=sim.size;rng=np.random.default_rng(91)
    u=rng.normal(0.,.01,3*N);direction=rng.normal(0.,1.,3*N);gate=np.full(N,.04)
    bc=(np.zeros(len(sim.contacts)),)*3
    r,scale,J,*_=sim._evaluate(u,gate,bc);h=1e-6
    difference=(sim._evaluate(u+h*direction,gate,bc,False)[0]-sim._evaluate(u-h*direction,gate,bc,False)[0])/(2*h)
    assert np.max(np.abs((difference-J@direction)/scale))<2e-5


@pytest.mark.parametrize('kind,gate',itertools.product(('graphene','mos2'),(-.1,.1)))
def test_equilibrium_nonuniform_gate_has_no_spurious_current(kind,gate):
    sim=device(kind);drive=gate*np.outer(np.linspace(.5,1.,sim.shape[0]),np.sin(np.pi*sim.x/sim.x[-1]))
    result=sim.solve(gate_voltage_V=drive);ledgers(result)
    assert np.max(np.abs(result['phi_V']))>1e-4
    assert np.max(np.abs(result['edge_currents_A']))<1e-20
    assert np.max(np.abs(result['Fn_eV']))<1e-15 and np.max(np.abs(result['Fp_eV']))<1e-15


@pytest.mark.parametrize('kind',['graphene','mos2'])
def test_low_bias_conductance_sign_and_width_scaling(kind):
    sim=device(kind);small=sim.solve(gate_voltage_V=0.,drain_voltage_V=1e-7);ledgers(small)
    st=sim.material.statistics();G=Q*(sim.mu_n*float(st.n_m2)+sim.mu_p*float(st.p_m2))*2
    assert small['terminal_currents_into_sheet_A']['drain']==pytest.approx(G*1e-7,rel=1e-4)
    wide=device(kind,width=4e-6);other=wide.solve(gate_voltage_V=.08,drain_voltage_V=.02)
    normal=sim.solve(gate_voltage_V=.08,drain_voltage_V=.02);ledgers(normal);ledgers(other)
    assert other['terminal_currents_into_sheet_A']['drain']==pytest.approx(2*normal['terminal_currents_into_sheet_A']['drain'],rel=2e-8)
    np.testing.assert_allclose(other['phi_V'],normal['phi_V'],atol=1e-10)


def test_genuinely_two_dimensional_gate_and_mobility_scaling():
    sim=device(nx=11,ny=7);gate=.12*np.outer(np.linspace(.1,1.,7),np.sin(np.pi*sim.x/sim.x[-1]))
    result=sim.solve(gate_voltage_V=gate,drain_voltage_V=.04);ledgers(result)
    y_edges=np.array([e[3]==1 for e in sim.edges])
    assert np.max(np.abs(result['edge_currents_A'][y_edges]))>1e-12
    scaled=device(nx=11,ny=7,multiplier=3.).solve(gate_voltage_V=gate,drain_voltage_V=.04);ledgers(scaled)
    np.testing.assert_allclose(scaled['phi_V'],result['phi_V'],atol=1e-10)
    assert scaled['terminal_currents_into_sheet_A']['drain']==pytest.approx(3*result['terminal_currents_into_sheet_A']['drain'],rel=2e-8)


@pytest.mark.parametrize('kind',['graphene','mos2'])
def test_mesh_refinement_of_smooth_gated_channel(kind):
    currents=[]
    # Resolve the nanometre contact screening layer. The original 100/50/25 nm
    # uniform cells do not reach the asymptotic regime at these SI parameters.
    for nx in (41,81,161):
        old=device(kind,nx=nx,ny=3)
        x=.5*(1-np.cos(np.linspace(0.,np.pi,nx)))*1e-6
        sim=SheetDriftDiffusion(x,old.y,old.material,gate_capacitance_F_m2=.02,
            mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01,sheet_permittivity_F=4e-20,
            doping_m2=old.doping.reshape(old.shape))
        result=sim.solve(gate_voltage_V=.08*np.sin(np.pi*sim.x/sim.x[-1])[None,:],drain_voltage_V=.02)
        ledgers(result);currents.append(result['terminal_currents_into_sheet_A']['drain'])
    assert abs(currents[2]-currents[1])<.4*abs(currents[1]-currents[0])


def test_failed_solve_does_not_mutate_device_or_masquerade_as_accepted_solution():
    sim=device();result=sim.solve(gate_voltage_V=.2,drain_voltage_V=.04,max_iter=1,tolerance=1e-14)
    assert not result['converged'] and result['status']=='max_iterations'
    assert result['residual_scaled_linf']>1e-14 and np.all(np.isfinite(result['phi_V']))
    clean=sim.solve(gate_voltage_V=.1,drain_voltage_V=.02);ledgers(clean)
    again=device().solve(gate_voltage_V=.1,drain_voltage_V=.02)
    np.testing.assert_array_equal(clean['phi_V'],again['phi_V'])
    result['phi_V'][:]=100.;np.testing.assert_array_equal(sim.solve(gate_voltage_V=.1,drain_voltage_V=.02)['phi_V'],again['phi_V'])


@pytest.mark.parametrize('kwargs',[{'gate_capacitance_F_m2':0.},{'mobility_n_m2_Vs':0.},
    {'sheet_permittivity_F':-1.},{'temperature_K':True},{'doping_m2':np.nan},
    {'x_m':[0.,0.]},{'y_m':[0.]},{'material':mos2_channel()}])
def test_invalid_device_inputs_rejected(kwargs):
    args=dict(x_m=[0.,1e-6],y_m=[0.,1e-6],material=graphene_sheet(),
        gate_capacitance_F_m2=.02,mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01)
    args.update(kwargs)
    with pytest.raises((ValueError,TypeError)):SheetDriftDiffusion(**args)
