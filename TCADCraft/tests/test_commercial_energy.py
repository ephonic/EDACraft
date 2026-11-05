import pytest
from tcad.postprocess.commercial_energy import audit_sentaurus_thermode_flux


def test_sentaurus_2d_w_per_um_conversion_and_sign():
    result=audit_sentaurus_thermode_flux(left_lheatflux=-1.,right_lheatflux=-1.5,
        left_voltage_V=0.,right_voltage_V=.01,right_current_A=500.,left_current_A=-500.,
        dimension='2d',depth_um=2.,relative_gate=1e-12)
    assert result['valid']
    assert result['outward_lattice_heat_power_W']==5.
    assert result['electrical_power_W']==5.
    assert result['lattice_power_residual_W']==0.
    assert result['complete_energy_closure'] is False


@pytest.mark.parametrize('dimension,kwargs',[
    ('1d',dict(area_um2=4.)),('2d',dict(depth_um=.5)),('3d',dict())])
def test_dimension_units_are_explicit(dimension,kwargs):
    result=audit_sentaurus_thermode_flux(left_lheatflux=-1.,right_lheatflux=0.,
        left_voltage_V=0.,right_voltage_V=0.,right_current_A=0.,dimension=dimension,**kwargs)
    assert result['source_unit'] in ('W','W/um','W/um2')


def test_invalid_dimension_and_nonfinite_values_rejected():
    with pytest.raises(ValueError):
        audit_sentaurus_thermode_flux(left_lheatflux=0.,right_lheatflux=0.,left_voltage_V=0.,
            right_voltage_V=0.,right_current_A=0.,dimension='2D')
    with pytest.raises(ValueError):
        audit_sentaurus_thermode_flux(left_lheatflux=float('nan'),right_lheatflux=0.,left_voltage_V=0.,
            right_voltage_V=0.,right_current_A=0.)
