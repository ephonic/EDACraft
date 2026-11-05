"""Independent prescribed pair counts and absorbed material energy.

No production generation helper, constitutive operator or native call is used.
The kinetic inputs are above the lowest matched valley edge. This is a declared
external source, not an absorption or photon-distribution calculation.
"""
import numpy as np
from tcad.solver.cut_cell_transport import _array


def generation_increments(model,dt):
    ld=np.longdouble;nc=model.nc
    rate=_array(model.pair_generation_rate_m3_s,nc,'pair generation rate',nonnegative=True).astype(ld)
    energies=[]
    for label,band,kinetic in (('electrons',model.Ec,model.pair_generation_kinetic_n_J),
                               ('holes',model.Eh,model.pair_generation_kinetic_p_J)):
        kinetic=_array(kinetic,nc,'injected kinetic energy',nonnegative=True).astype(ld)
        energies.append(np.asarray(band,ld)+ld(min(v.band_offset_owner_J for v in model.valleys[label]))+kinetic)
    total=energies[0]+energies[1]
    if (any(not np.all(np.isfinite(v)) for v in energies) or
        np.any((rate>0)&((total<=0)|~np.isfinite(total)))):
        raise ValueError('finite material energies and positive absorbed energy per generated pair required')
    count=ld(dt)*model.vol.astype(ld)*rate
    deposited=[count*v for v in energies]
    if any(not np.all(np.isfinite(v)) for v in (count,*deposited)):
        raise ValueError('independent generation increments outside finite range')
    return count,deposited
