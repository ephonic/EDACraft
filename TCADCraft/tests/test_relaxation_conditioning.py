"""Finite constitutive products with overflowing intermediate powers.

Extreme exponents are numerical controls, never material calibrations.
"""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal, localcontext
import numpy as np
import pytest
from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw as Law
from tcad.postprocess.three_temperature_energy import _reference_relaxation_times, audit_three_temperature_energy
from test_three_temperature import case, BUDGET


@pytest.mark.parametrize('sign', [-1, 1])
@pytest.mark.parametrize('pair', ['lattice_density', 'lattice_carrier', 'carrier_density'])
def test_overflowing_powers_match_independent_decimal_product(sign, pair):
    a,b,c = {'lattice_density': (20000,0,-40000),
        'lattice_carrier': (20000,-40000,0), 'carrier_density': (0,20000,-20000)}[pair]
    law=Law(150.,1e25,*[sign*x for x in (a,b,c)])
    tau=np.array([1e-13,4e-13],np.longdouble)
    density=np.array([2e25,2e25],np.longdouble)
    tc=np.array([300.,300.]);tl=np.array([600.,600.])
    # This oracle evaluates a high-precision direct product, not logarithms.
    with localcontext() as context:
        context.prec=100
        factor=Decimal(4)**(sign*a)*Decimal(2)**(sign*b)*Decimal(2)**(sign*c)
    assert abs(factor-1)<Decimal('1e-95')
    actual=_reference_relaxation_times(tau,density,tc,tl,law)
    np.testing.assert_allclose(actual,tau,rtol=2e-15,atol=0)


@pytest.mark.parametrize('sign', [-1,1])
@pytest.mark.parametrize('pair', ['lattice_density','lattice_carrier','carrier_density'])
def test_actual_native_equilibrium_step_reaudits_without_native_operators(sign,pair,monkeypatch):
    model,old=case(count=1,uniform=True)
    old=replace(old,electron_temperature_K=[300.],hole_temperature_K=[300.])
    exponents={'lattice_density': (20000,0,-20000),
        'lattice_carrier': (20000,-20000,0),'carrier_density': (0,20000,-20000)}[pair]
    law=Law(150.,1e25/2,*[sign*x for x in exponents])
    model.relaxation_laws=(law,law)
    new,report=model.step(old,2e-13,**BUDGET)
    assert report['independent_audit']['valid']
    for label,tau in [('electrons',1e-13),('holes',4e-13)]:
        np.testing.assert_allclose(report['cell_relaxation_time_s'][label],tau,rtol=1e-12,atol=0)
    import tcad.core as public
    import tcad.core._bindings as native
    def deny(*a,**k):raise AssertionError('native or production law called in independent replay')
    for module in (public,native):
        for name in dir(module):
            if (name.startswith('native_') or name.startswith('three_temperature_')) and callable(getattr(module,name)):
                monkeypatch.setattr(module,name,deny)
    monkeypatch.setattr(Law,'evaluate',deny)
    assert audit_three_temperature_energy(model,old,new,report,**BUDGET)['valid']
    forged=deepcopy(report)
    forged['cell_relaxation_time_s']['electrons']=np.array([1.1e-13])
    assert not audit_three_temperature_energy(model,old,new,forged,**BUDGET)['valid']
    assert not report['physical_validated'] and not report['complete_device_energy']


@pytest.mark.parametrize('sign', [-1,1])
def test_nonrepresentable_final_times_remain_rejected(sign):
    law=Law(150.,1e25,sign*20000,0,0)
    with pytest.raises(ValueError,match='out of range'):
        _reference_relaxation_times([1e-13],[1e25],[300.],[300.],law)


def test_ordinary_product_arithmetic_is_unchanged():
    law=Law(300.,1e25,.6,1.2,-.25)
    tau=np.array([1e-13,4e-13],np.longdouble)
    n=np.array([2e25,3e25],np.longdouble);tc=np.array([330.,280.],np.longdouble);tl=np.array([305.,310.],np.longdouble)
    expected=tau*(tl/np.longdouble(300))**.6
    expected=expected*(tc/np.longdouble(300))**1.2
    expected=expected*(n/np.longdouble(1e25))**-.25
    np.testing.assert_array_equal(_reference_relaxation_times(tau,n,tc,tl,law),expected)
