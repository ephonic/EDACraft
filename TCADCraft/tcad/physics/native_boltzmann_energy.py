"""Explicit native MB signed energy coordinates; no device statistics switch."""
import numpy as np
from .native_boltzmann import _numbers,_valleys,_view
from .native_fermi_local import _decimal


def native_boltzmann_energy_coordinates(densities,reference_temperatures,values,bands,valleys,
                                        *,initialize=False,max_iterations=128):
    """Encode physical temperatures or decode signed excess over reference T.

    Native decimal excess is authoritative. Temperature and the EOS residual
    describe its finite-precision inversion; total energy may also round.
    This primitive neither advances a device nor provides collision sources.
    """
    from tcad.core._bindings import native_boltzmann_energy_coordinates_raw
    if type(initialize) is not bool or isinstance(max_iterations,(bool,np.bool_)) or not isinstance(max_iterations,(int,np.integer)):
        raise ValueError('boolean initialization and integer iteration budget required')
    first=np.asarray(densities)
    if first.ndim!=1 or not first.size:raise ValueError('nonempty MB energy vectors required')
    arrays=[_numbers(a,first.shape) for a in (densities,reference_temperatures,values,bands)]
    _,packed=_valleys(valleys)
    raw=native_boltzmann_energy_coordinates_raw([_decimal(v) for row in zip(*arrays) for v in row],packed,initialize,max_iterations)
    if len(raw)!=10*len(first):raise ValueError('native MB energy output coverage mismatch')
    keys=('temperature_K','reference_thermal_energy_J_m3','excess_energy_J_m3','EOS_residual_J_m3',
          'residual_budget_J_m3','heat_capacity_J_m3_K','chemical_potential_J','energy_density_J_m3','energy_origin_J','iterations')
    result=[]
    for i in range(len(first)):
        text=tuple(raw[10*i:10*(i+1)]);row=_view(text)
        result.append(dict(zip(keys,row),native_decimal=text,statistics='boltzmann',
            execution_backend='native',excess_authoritative=True,device_statistics_selected=False))
    return result
