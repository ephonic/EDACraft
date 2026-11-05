"""Independent internal exchange and float64 temperature-rounding allowance.

The signed-energy EOS supplies rounded transport temperatures. Their exact
rounding cells have half the adjacent float64 spacing on either side. Charge
the worst corresponding error in dt*V*G*(Tn-Tp) to each carrier energy budget.
This allowance does not certify EOS/quadrature or global temporal accuracy.
"""
import numpy as np
from tcad.solver.cut_cell_transport import _array


def exchange_increments(model,state,dt):
    ld=np.longdouble
    g=_array(model.intercarrier_conductance_W_m3_K,model.nc,'intercarrier conductance',nonnegative=True).astype(ld)
    widths=[];temperatures=[]
    for values in (state.electron_temperature_K,state.hole_temperature_K):
        view=np.asarray(values,float);temperatures.append(view.astype(ld))
        widths.append(np.maximum(view.astype(ld)-np.nextafter(view,-np.inf).astype(ld),
                                 np.nextafter(view,np.inf).astype(ld)-view.astype(ld))/2)
    factor=ld(dt)*model.vol.astype(ld)*g
    transfer=factor*(temperatures[0]-temperatures[1])
    bound=factor*(widths[0]+widths[1])
    if not np.all(np.isfinite(transfer)) or not np.all(np.isfinite(bound)):
        raise ValueError('finite intercarrier transfer and rounding allowance required')
    return transfer,bound
