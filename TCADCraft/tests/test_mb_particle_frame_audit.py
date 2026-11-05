from dataclasses import replace
from decimal import Decimal,localcontext
from copy import deepcopy
import pytest
from tcad.solver.boltzmann_particle_energy import expand_mb_relaxation_state as expand,update_mb_particle_energy as update
from tcad.postprocess.boltzmann_particle_energy import audit_mb_particle_energy as audit
from tcad.solver.boltzmann_relaxation import MBRelaxationConfiguration as Config,initialize_mb_relaxation as initialize
from tcad.physics.multivalley_thermionic import ThermionicValley
from tests.test_mb_particle_energy import make


@pytest.mark.parametrize('sign',[1,-1])
def test_micro_density_frame_drift_cannot_hide_inside_command_rounding_envelope(sign):
    cfg,s=make();old=expand(cfg,s);n=list(map(float,old.frame[:2]));new,r=update(old,n,[0.,0.])
    with localcontext() as ctx:
        ctx.prec=100
        forged=replace(new,frame=(str(Decimal(new.frame[0])+sign*Decimal('1e-8')),*new.frame[1:]))
    # This density drift is below the command rounding envelope. Energy must
    # nevertheless be derived from the submitted frame and meet zero signal.
    result=audit(old,forged,r,densities=n,bands_J=[0.,0.],energy_impulses_J=[0.,0.],energy_atol_J=1e-27)
    assert not result['valid'] and Decimal(result['carrier_energy_budgets_J'][0])==0


@pytest.mark.parametrize('En,Ep',[(3e-21,-2e-21),(-2e-21,3e-21)])
def test_true_noop_preserves_nonzero_native_band_frame_strings(En,Ep):
    vn=(ThermionicValley('n',1,.3,.3,.3,En,En),);vp=(ThermionicValley('p',1,.3,.3,.3,Ep,Ep),)
    cfg=Config.create(1000.,1e-20,3e-13,2e-13,vn,vp,temperature_bounds=(150.,700.))
    old=expand(cfg,initialize(cfg,[1e25,1e25],300.,[310.,400.,250.]))
    new,r=update(old,[1e25,1e25],[En,Ep])
    assert new.frame==old.frame and new.electron_excess==old.electron_excess and new.hole_excess==old.hole_excess
    assert r['independent_audit']['valid'] and all(Decimal(x)==0 for x in r['independent_audit']['carrier_energy_residuals_J'])
