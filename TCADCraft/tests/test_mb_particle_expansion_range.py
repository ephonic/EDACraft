"""Independent cancellation/range probes, not particle trajectories."""
from dataclasses import replace
from decimal import Decimal,localcontext
import pytest
from tcad.solver.boltzmann_particle_energy import expand_mb_relaxation_state as expand,update_mb_particle_energy as update
from tcad.solver.boltzmann_relaxation import MBRelaxationConfiguration as Config,initialize_mb_relaxation as initialize
from tcad.physics.multivalley_thermionic import ThermionicValley
from tcad.core._bindings import native_boltzmann_particle_energy_raw as raw
from tests.test_mb_particle_energy import make


@pytest.mark.parametrize('tail,density',[('1e-300','1e-278'),('-1e-300','1e-278'),('1e-80','1e-58'),('-1e-80','1e-58')])
def test_native_cancellation_recovers_tiny_value_before_temperature_view(tail,density):
    cfg,s=make();old=replace(expand(cfg,s),electron_excess=(tail,),hole_excess=(tail,))
    new,_=update(old,[1.1e25,.9e25],[1e-21,-1e-21])
    back,_=update(new,[float(old.frame[0]),float(old.frame[1])],[0.,0.])
    # A new diagnostic state uses a small density to resolve the same energy
    # expansion in temperature. This is not a physical density update/trajectory.
    f=(density,density,*back.frame[2:])
    values=raw(f,back.electron_excess,back.hole_excess,[density,density,'0','0','0','0'])
    with localcontext() as ctx:
        ctx.prec=100
        expected=Decimal(310)+Decimal(tail)/(Decimal('1.5')*Decimal('1.380649e-23')*Decimal(density))
    assert float(values[-2])==pytest.approx(float(expected),rel=1e-14)
    assert float(values[-1])==pytest.approx(float(expected),rel=1e-14)


@pytest.mark.parametrize('En,Ep',[(3e-21,-2e-21),(-2e-21,3e-21)])
def test_density_change_with_initial_nonzero_band_background(En,Ep):
    vn=(ThermionicValley('n',1,.3,.3,.3,band_offset_owner_J=En,band_offset_neighbor_J=En),)
    vp=(ThermionicValley('p',1,.3,.3,.3,band_offset_owner_J=Ep,band_offset_neighbor_J=Ep),)
    cfg=Config.create(1000.,1e-20,3e-13,2e-13,vn,vp,temperature_bounds=(150.,700.))
    s=initialize(cfg,[1e25,1e25],300.,[310.,400.,250.]);old=expand(cfg,s)
    new,r=update(old,[1.1e25,.9e25],[En,Ep])
    assert r['independent_audit']['valid']
    with localcontext() as ctx:
        ctx.prec=100
        alpha=Decimal('1.5')*Decimal('1.380649e-23')
        for k,T in enumerate((400,250)):
            n0=Decimal(old.frame[k]);n1=Decimal(new.frame[k]);E0=Decimal(old.frame[5+k]);E1=Decimal(new.frame[5+k])
            expected=(n0*(E0+alpha*Decimal(T))/n1-E1)/alpha
            assert float(r['temperatures_K'][k+1])==pytest.approx(float(expected),rel=1e-14)
