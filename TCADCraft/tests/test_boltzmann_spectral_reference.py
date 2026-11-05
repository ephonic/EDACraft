"""Analytic MB moments, thermodynamic symmetry and independently integrated FD limit."""
import math
import numpy as np
import pytest
from tcad.physics.multivalley_thermionic import ThermionicValley
from tcad.postprocess.boltzmann_spectral_reference import (
    KB, Q, boltzmann_reservoir, boltzmann_bulk_face)
from tcad.postprocess.fermi_spectral_energy import reference_reservoir, reference_face

VALLEYS = (ThermionicValley('one', 1, .3, .3, .3),)
GEOM = dict(phi_o=0., phi_n=0., phi_f=0., z=-1,
            mu_o=.03, mu_n=.02, area=1e-13, do=2e-9, dn=3e-9)


@pytest.mark.parametrize('to,tn,no,nn', [(600., 600., 2e21, 1e21), (900., 450., 1e21, 2e21),
                                       (450., 900., 2e21, 1e21), (600., 600., 1e21, 1e21)])
@pytest.mark.parametrize('path', ['linear_series', 'endpoint_barrier'])
def test_closed_form_flat_potential(to, tn, no, nn, path):
    band = .5*Q
    one, two = [boltzmann_reservoir(n, t, band, VALLEYS) for n,t in ((no,to),(nn,tn))]
    actual = boltzmann_bulk_face(one, two, VALLEYS, **GEOM, bulk_potential_path=path)
    factor = GEOM['area']/(GEOM['do']/GEOM['mu_o']+GEOM['dn']/GEOM['mu_n'])*KB/Q
    particle = factor*(no*to-nn*tn)
    energy = band*particle+2.5*KB*factor*(no*to**2-nn*tn**2)
    particle_scale = factor*(no*to+nn*tn)
    energy_scale = abs(band)*particle_scale+2.5*KB*factor*(no*to**2+nn*tn**2)
    assert abs(actual['particle_flux_s']-particle) <= 2e-12*particle_scale
    assert abs(actual['material_energy_flux_W']-energy) <= 2e-12*energy_scale
    entropy = ((one['chemical_potential_J']/to-two['chemical_potential_J']/tn)*particle
               +(1/tn-1/to)*energy)
    assert actual['entropy_production_W_K'] == pytest.approx(entropy, rel=3e-12, abs=1e-28)
    assert actual['entropy_production_W_K'] >= 0
    assert one['energy_density_J_m3'] == pytest.approx(no*(band+1.5*KB*to), rel=1e-14)


@pytest.mark.parametrize('z', [-1, 1])
def test_reversal_and_electrostatic_gauge(z):
    one = boltzmann_reservoir(2e21, 750., .3*Q, VALLEYS)
    two = boltzmann_reservoir(1e21, 500., .3*Q, VALLEYS)
    kwargs = dict(GEOM, phi_o=.01, phi_n=-.02, phi_f=-.005, z=z)
    forward = boltzmann_bulk_face(one, two, VALLEYS, **kwargs)
    reverse = boltzmann_bulk_face(two, one, VALLEYS, **dict(kwargs,
        phi_o=kwargs['phi_n'], phi_n=kwargs['phi_o'], do=kwargs['dn'], dn=kwargs['do'],
        mu_o=kwargs['mu_n'], mu_n=kwargs['mu_o']))
    gauge = boltzmann_bulk_face(one, two, VALLEYS, **dict(kwargs,
        phi_o=kwargs['phi_o']+.2, phi_n=kwargs['phi_n']+.2, phi_f=kwargs['phi_f']+.2))
    for key in ('particle_flux_s', 'material_energy_flux_W'):
        assert reverse[key] == pytest.approx(-forward[key], rel=2e-12)
        assert gauge[key] == pytest.approx(forward[key], rel=2e-12)
    assert reverse['entropy_production_W_K'] == pytest.approx(forward['entropy_production_W_K'], rel=2e-12)
    assert gauge['entropy_production_W_K'] == pytest.approx(forward['entropy_production_W_K'], rel=2e-12)


def test_independent_fd_dilute_limit_and_zero_neighbor_distance():
    args = [(1e14, 700., .4*Q, VALLEYS), (2e14, 500., .4*Q, VALLEYS)]
    mb = [boltzmann_reservoir(*v) for v in args]
    fd = [reference_reservoir(*v) for v in args]
    geom = dict(GEOM, phi_o=.012, phi_n=-.01, phi_f=-.01, dn=0.)
    a = boltzmann_bulk_face(*mb, VALLEYS, **geom)
    b = reference_face(*fd, VALLEYS, **geom, bulk_potential_path='linear_series')
    for key in ('particle_flux_s', 'material_energy_flux_W', 'entropy_production_W_K'):
        assert a[key] == pytest.approx(b[key], rel=2e-9)


def test_multivalley_partition_and_band_reference():
    vs = VALLEYS+(ThermionicValley('two', 2, .3, .3, .3, .04*Q, .04*Q),)
    n,t = 2e21, 650.
    r = boltzmann_reservoir(n,t,.3*Q,vs)
    ratio = 2*math.exp(-.04*Q/(KB*t))
    assert r['valley_populations_m3'][1]/r['valley_populations_m3'][0] == pytest.approx(ratio)
    assert sum(r['valley_populations_m3']) == pytest.approx(n)
    expected = n*(.3*Q+1.5*KB*t+.04*Q*ratio/(1+ratio))
    assert r['energy_density_J_m3'] == pytest.approx(expected)


@pytest.mark.parametrize('key,value', [('dn', -1.), ('do', 0.), ('mu_o', 0.), ('area', float('nan')),
                                     ('z', True), ('bulk_potential_path', 'unknown')])
def test_invalid_face_contract(key, value):
    r = boltzmann_reservoir(1e21,600.,0.,VALLEYS)
    with pytest.raises(ValueError):
        boltzmann_bulk_face(r,r,VALLEYS,**dict(GEOM,**{key:value}))


def test_explicit_statistics_and_offset_scope():
    r = boltzmann_reservoir(1e21,600.,0.,VALLEYS)
    with pytest.raises(ValueError, match='explicit MB'):
        boltzmann_bulk_face(dict(r,statistics='fermi_dirac'),r,VALLEYS,**GEOM)
    with pytest.raises(ValueError, match='same valley offset'):
        boltzmann_reservoir(1e21,600.,0.,(ThermionicValley('step',1,.3,.3,.3,0.,Q*.1),))


@pytest.mark.parametrize('n,t', [(0.,600.), (1e21,float('inf')), (True,600.), (1e21,-1.)])
def test_invalid_reservoir(n,t):
    with pytest.raises(ValueError):
        boltzmann_reservoir(n,t,0.,VALLEYS)
