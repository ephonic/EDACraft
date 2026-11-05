"""Calibration identifiability, units, spinodal physics and explicit dynamics."""
import math
import pytest
from tcad.material.calibration import fit_static_landau, published_alscn_2025_static


def test_published_film_units_spinodal_and_provenance():
    c=published_alscn_2025_static()
    assert c.remanence_C_m2==pytest.approx(1.05)
    assert c.coercive_field_V_m==7e8
    pr=math.sqrt(-c.alpha/c.beta)
    pc=pr/math.sqrt(3)
    assert c.alpha*pr+c.beta*pr**3==pytest.approx(0.,abs=1e-6)
    assert c.alpha+3*c.beta*pc**2==pytest.approx(0.,abs=1e-6)
    assert abs(c.alpha*pc+c.beta*pc**3)==pytest.approx(7e8)
    # Positive curvature at remanence, negative at P=0; SI field scale intact.
    assert c.alpha+3*c.beta*pr**2>0 and c.alpha<0
    report=c.report()
    assert report['dynamic_viscosity'] is None
    assert report['experimental_uncertainty'] is None
    assert not report['independent_validation'] and not report['physical_validated']
    assert '62904' in report['source'] and 'AlN insert=0' in report['specimen']


@pytest.mark.parametrize('pr,ec',[(1.05,7e8),(.2,1e8),(1.4,3.5e8)])
def test_fits_distinct_materials_without_composition_extrapolation(pr,ec):
    c=fit_static_landau(pr,ec,source='measurement',specimen='specific sample')
    assert math.sqrt(-c.alpha/c.beta)==pytest.approx(pr)
    assert 2*abs(c.alpha)*pr/(3*math.sqrt(3))==pytest.approx(ec)


@pytest.mark.parametrize('bad',[0,-1,float('nan'),float('inf'),True,None,[],1e-300,1e300])
@pytest.mark.parametrize('parameter',['remanence_C_m2','coercive_field_V_m'])
def test_invalid_or_unrepresentable_calibration_rejected(parameter,bad):
    args=dict(remanence_C_m2=1.,coercive_field_V_m=1e8,source='source',specimen='film')
    args[parameter]=bad
    # Extreme coercive fields still have representable coefficients at Pr=1.
    if parameter=='coercive_field_V_m' and bad in (1e-300,1e300):return
    with pytest.raises(ValueError):fit_static_landau(**args)


@pytest.mark.parametrize('field',['source','specimen'])
@pytest.mark.parametrize('value',['',' ',None,1])
def test_untraceable_measurements_rejected(field,value):
    args=dict(source='source',specimen='film');args[field]=value
    with pytest.raises(ValueError):fit_static_landau(1.,1e8,**args)


def test_explicit_viscosity_required_and_bad_input_does_not_mutate():
    calls=[]
    class Target:
        def set_ferroelectric_params(self,*args):calls.append(('params',args))
        def set_ferroelectric_gamma(self,*args):calls.append(('gamma',args))
    c=published_alscn_2025_static();sim=Target()
    with pytest.raises(TypeError):c.configure_lk(sim,[1])
    with pytest.raises(ValueError):c.configure_lk(sim,[1],viscosity=0)
    assert calls==[]
    c.configure_lk(sim,[1],viscosity=.1)
    assert calls==[('params',([1],c.alpha,c.beta)),('gamma',(.1,))]
