from decimal import Decimal
import numpy as np
import pytest
from tcad.core._bindings import native_fermi_energy_coordinates_raw as raw
from tcad.physics.native_fermi_local import _decimal
from tcad.postprocess.fermi_spectral_energy import reference_reservoir
from test_fermi_spectral import VALLEYS

PACKED=tuple(v for valley in VALLEYS for v in (valley.mass_normal,valley.dos_mass_ratio,valley.degeneracy,valley.band_offset_owner_J))


@pytest.mark.parametrize('n,Tl,Tc',[(1e17,300,450),(1e25,300,360),(1e25,300,260),(1e26,450,300)])
def test_FD_temperature_roundtrip_and_independent_DOS(n,Tl,Tc):
    result=raw(list(map(_decimal,(n,Tl,Tc,0))),PACKED,True)
    assert float(result[0])==Tc
    replay=raw([_decimal(n),_decimal(Tl),result[2],'0'],PACKED)
    assert result==replay
    expected=reference_reservoir(n,Tl,0,VALLEYS)['energy_density_J_m3']
    assert float(result[1])==pytest.approx(expected,rel=1e-11)
    assert Decimal(result[4])<=Decimal(result[2])<=Decimal(result[5])


@pytest.mark.parametrize('energy',['1e-80','-1e-80','1e-300','-1e-300'])
def test_sub_ULP_energy_remains_authoritative_without_a_fictitious_temperature(energy):
    result=raw(['1e25','303',energy,'0'],PACKED)
    assert float(result[0])==303 and abs(Decimal(result[2])/Decimal(energy)-1)<Decimal('1e-32')
    assert Decimal(result[3])==Decimal(result[2]).copy_negate()
    assert Decimal(result[4])<0<Decimal(result[5])
    assert Decimal(result[4])<=Decimal(energy)<=Decimal(result[5])


@pytest.mark.parametrize('energy',['-1e10','1e10','nan'])
def test_invalid_carrier_energy_is_rejected(energy):
    with pytest.raises(ValueError):raw(['1e25','303',energy,'0'],PACKED)
