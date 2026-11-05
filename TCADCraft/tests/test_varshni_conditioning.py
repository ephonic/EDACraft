"""Conditioned effective band laws, Decimal oracles and actual native work.

Extreme coefficients are numerical controls, not material calibrations.
"""
from decimal import Decimal,localcontext
from copy import deepcopy
import numpy as np
import pytest
from test_temperature_dependent_bands import band_case
from test_varshni_temperature_bands import configure
from test_three_temperature import BUDGET
from tcad.solver.cut_cell_transport import Q
from tcad.postprocess.three_temperature_energy import reference_band_edges,audit_three_temperature_energy


def oracle(model,t):
    with localcontext() as ctx:
        ctx.prec=100
        d=lambda x:Decimal.from_float(float(x))
        T=d(t);R=d(model.T);edges=[];slopes=[]
        for i in range(2):
            B=d(model.band_varshni_beta[i][0]);A=d(model.band_varshni_alpha[i][0])
            S=d(model.band_temperature_slopes[i][0]);E=d((model.Ec,model.Eh)[i][0])
            edges.append(float(E+(T-R)*(S-A*(T*R+B*(T+R))/((T+B)*(R+B)))))
            slopes.append(float(S-A*T*(T+2*B)/(T+B)**2))
        return np.array(edges),np.array(slopes)


def conditioned_case(beta,sign=1.,complex=False):
    model,old=band_case(complex=complex);configure(model,sign=sign,beta=beta)
    # Keep the physical-size band slope resolved even when beta is huge.
    if beta>1e10:
        model.band_varshni_alpha=tuple(np.array([sign*beta*v*Q/600]) for v in (2.365e-4,1.5e-4))
    return model,old


@pytest.mark.parametrize('beta',[0.,636.,1e20,1e100,1e308])
@pytest.mark.parametrize('sign',[-1.,1.])
@pytest.mark.parametrize('temperature',[np.nextafter(300.,np.inf),305.,400.])
def test_band_values_and_capacity_derivatives_match_decimal(beta,sign,temperature):
    model,_=conditioned_case(beta,sign)
    expected,derivative=oracle(model,temperature)
    with np.errstate(over='raise',invalid='raise',divide='raise'):
        actual=np.array(model.band_edges([temperature]))[:,0]
        slopes=np.array(model.band_derivatives([temperature]),float)[:,0]
        audit=np.array(reference_band_edges(model,[temperature]))[:,0]
    np.testing.assert_allclose(actual,expected,rtol=3e-15,atol=1e-35)
    np.testing.assert_allclose(audit,expected,rtol=3e-15,atol=1e-35)
    np.testing.assert_allclose(slopes,derivative,rtol=3e-15,atol=1e-39)


@pytest.mark.parametrize('beta',[1e20,1e308])
@pytest.mark.parametrize('complex',[False,True])
def test_resolved_large_beta_band_work_in_native_steps_and_independent_replay(beta,complex,monkeypatch):
    model,old=conditioned_case(beta,complex=complex)
    new,report=model.step(old,1e-15 if complex else 2e-13,**BUDGET)
    assert report['independent_audit']['valid']
    assert any(np.any(np.asarray(x)!=0) for x in report['cell_band_work_from_lattice_J'].values())
    import tcad.core as public
    import tcad.core._bindings as native
    def deny(*a,**k):raise AssertionError('native operator forbidden during independent replay')
    for module in (public,native):
        for name in dir(module):
            if (name.startswith('native_') or name.startswith('three_temperature_')) and callable(getattr(module,name)):
                monkeypatch.setattr(module,name,deny)
    audit=audit_three_temperature_energy(model,old,new,report,**BUDGET)
    assert audit['valid']
    for key in ('electrons','holes'):
        expected=float(np.sum(report['cell_band_work_from_lattice_J'][key],dtype=np.longdouble))
        assert expected!=0
        # Check the resolved ledger value itself even below the acceptance
        # budget. A cancellation to zero must not pass by absolute tolerance.
        np.testing.assert_allclose(audit['independently_reconstructed_ledger']['band_work_from_lattice_J'][key],
            expected,rtol=3e-12,atol=0)
    forged=deepcopy(report)
    forged['cell_band_work_from_lattice_J']['electrons']=np.full(model.nc,100*BUDGET['energy_atol_J'])
    assert not audit_three_temperature_energy(model,old,new,forged,**BUDGET)['valid']
    assert not report['temperature_dependent_band_entropy_closed']
    assert not report['complete_device_energy']
