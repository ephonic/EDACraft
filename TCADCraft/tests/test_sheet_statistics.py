"""Independent ideal-band integrals, derivatives and SI sheet units."""
import math
import numpy as np
import pytest
from scipy.integrate import quad
from scipy.special import expit
from tcad.material.sheet import Q, KB, HBAR, M0, SheetMaterial, fermi_one, graphene_sheet, mos2_sheet


@pytest.mark.parametrize('eta',[-100.,-40.,-10.,-1.,-.01,0.,.01,1.,5.,40.,100.])
def test_fermi_integral_against_independent_quadrature(eta):
    # Scale out the negative fugacity so absolute integration tolerance cannot
    # accept zero as the tiny but nonzero Boltzmann tail.
    if eta<0:
        expected=math.exp(eta)*quad(lambda x:x*math.exp(-x)/(1+math.exp(eta-x)),0.,100.,epsabs=2e-13,epsrel=2e-13)[0]
    else:
        expected=quad(lambda x:x*expit(eta-x),0.,eta+100.,epsabs=2e-11,epsrel=2e-13,points=[eta])[0]
    assert math.isclose(float(fermi_one(eta)),expected,rel_tol=2e-12)


@pytest.mark.parametrize('model',['mos2','graphene'])
@pytest.mark.parametrize('temperature',[100.,300.,600.])
@pytest.mark.parametrize('eta',[-30.,-2.,0.,2.,30.])
def test_sheet_density_derivatives_and_direct_dos_integral(model,temperature,eta):
    material=mos2_sheet() if model=='mos2' else graphene_sheet()
    vt=KB*temperature/Q
    edge=material.reference_eV+material.gap_eV/2
    mu=edge+eta*vt
    st=material.statistics(0.,mu,mu,temperature)
    if model=='mos2':
        pref=material.degeneracy_n*material.mass_n_m0*M0*KB*temperature/(2*math.pi*HBAR**2)
        order=0
    else:
        pref=material.degeneracy_n/(2*math.pi)*(KB*temperature/(HBAR*material.fermi_velocity_m_s))**2
        order=1
    if eta<0:
        integral=math.exp(eta)*quad(lambda x:x**order*math.exp(-x)/(1+math.exp(eta-x)),0.,100.,epsabs=2e-13,epsrel=2e-13)[0]
    else:
        integral=quad(lambda x:x**order*expit(eta-x),0.,eta+100.,epsabs=2e-12,epsrel=2e-13,points=[eta])[0]
    assert math.isclose(float(st.n_m2),pref*integral,rel_tol=1e-10)
    step=vt*1e-4
    plus=material.statistics(step,mu,mu,temperature)
    minus=material.statistics(-step,mu,mu,temperature)
    np.testing.assert_allclose((plus.n_m2-minus.n_m2)/(2*step),st.dn_dFn_m2_eV,rtol=2e-8)
    np.testing.assert_allclose((minus.p_m2-plus.p_m2)/(2*step),st.minus_dp_dFp_m2_eV,rtol=2e-8)
    np.testing.assert_allclose(-(plus.charge_C_m2-minus.charge_C_m2)/(2*step),st.quantum_capacitance_F_m2,rtol=2e-8)


@pytest.mark.parametrize('temperature',[30.,300.,900.])
def test_graphene_neutrality_intrinsic_and_quantum_capacitance(temperature):
    material=graphene_sheet();st=material.statistics(temperature_K=temperature)
    expected_n=math.pi/6*(KB*temperature/(HBAR*1e6))**2
    expected_c=4*math.log(2)*Q**2*KB*temperature/(math.pi*(HBAR*1e6)**2)
    assert math.isclose(float(st.n_m2),expected_n,rel_tol=2e-15)
    assert float(st.n_m2)==float(st.p_m2) and float(st.charge_C_m2)==0.
    assert math.isclose(float(st.quantum_capacitance_F_m2),expected_c,rel_tol=2e-15)
    for phi in (-1e-20,1e-20):
        tiny=material.statistics(phi,temperature_K=temperature)
        assert math.isclose(float(tiny.charge_C_m2),-expected_c*phi,rel_tol=3e-15)


@pytest.mark.parametrize('material',[mos2_sheet(),graphene_sheet()])
def test_gauge_invariance_independent_quasi_fermi_levels_and_array_ownership(material):
    # Dyadic shifts avoid changing the represented physical energy through
    # decimal cancellation when testing a relative error at neutral charge.
    phi=np.array([-.125,.03125,.25]);fn=np.array([.125,-.015625,.0625]);fp=fn-.015625
    original=material.statistics(phi,fn,fp)
    shifted=material.statistics(phi+.25,fn-.25,fp-.25)
    for name in original.__dataclass_fields__:
        np.testing.assert_allclose(getattr(original,name),getattr(shifted,name),rtol=5e-14,atol=1e-24)
    assert np.all(material.statistics(phi,fn,fp-.01).p_m2>original.p_m2)
    with pytest.raises(ValueError):original.n_m2[0]=0
    old=original.n_m2.copy();phi[:]=10.;np.testing.assert_array_equal(original.n_m2,old)


@pytest.mark.parametrize('value',[0.,-1.,float('nan'),float('inf'),True,[300.]])
def test_invalid_temperature_rejected(value):
    with pytest.raises(ValueError):graphene_sheet().statistics(temperature_K=value)


@pytest.mark.parametrize('kwargs',[{'dispersion':'bulk'},{'gap_eV':-1.},{'mass_n_m0':0.},
    {'degeneracy_n':True},{'fermi_velocity_m_s':float('inf')},{'reference_eV':[0.]},
    {'dispersion':'dirac','gap_eV':1.},{'dispersion':'dirac','degeneracy_n':4.,'degeneracy_p':2.}])
def test_invalid_band_models_rejected(kwargs):
    args=dict(name='invalid',dispersion='parabolic');args.update(kwargs)
    with pytest.raises(ValueError):SheetMaterial(**args)


def test_degenerate_limit_and_nonfinite_energy_rejection():
    material=graphene_sheet();mu=.2;st=material.statistics(Fn_eV=mu,temperature_K=.1)
    expected=mu**2*Q**2/(math.pi*(HBAR*1e6)**2)
    assert math.isclose(float(st.n_m2),expected,rel_tol=1e-8)
    with pytest.raises(ValueError):material.statistics(phi_V=np.nan)
    with pytest.raises(ValueError):material.statistics(phi_V=True)
    with pytest.raises(OverflowError):fermi_one(1e300)
