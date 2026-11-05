"""Whole-device stopping budgets, computed from the exported candidate ledger.

These tests guide Newton effort. The public step and independent postprocessor
still check conservation before the device can commit its candidate.
"""
import numpy as np
from .cut_cell_transport import Q


def global_conservation_merit(model, old, cache, old_poisson, dt,
                              charge_atol_C, energy_atol_J):
    ld = np.longdouble
    boundary = np.array([f for f, face in enumerate(model.mesh.faces) if face.neighbor < 0], int)
    new_poisson = cache['poisson']
    qflux = Q*(cache['rates']['holes']-cache['rates']['electrons'])
    dq = new_poisson['integrated_D_flux_C']-old_poisson['integrated_D_flux_C']
    displacement = -sum(value*dq[f] for f, value in model.bc.items())
    conduction = -dt*sum(value*qflux[f] for f, value in model.bc.items())
    increments = [float(np.sum(cache['du'][s], dtype=ld)) for s in ('electrons', 'holes')]
    increments += [float(np.sum(cache['dl'], dtype=ld)),
                   float(ld(new_poisson['electrostatic_energy_J'])-ld(old_poisson['electrostatic_energy_J']))]
    if model.trap_capture_law is not None:
        increments.append(float(np.sum(cache['trap_energy_increment_J'], dtype=ld)))
    outward = [dt*float(np.sum(cache['energies'][s][boundary], dtype=ld)) for s in ('electrons', 'holes')]
    outward.append(dt*float(np.sum(cache['heat'][boundary], dtype=ld)))
    if model.radiative_law is not None:
        outward.append(float(np.sum(cache['radiative_photon_energy_J'], dtype=ld)))
    absorbed = sum(np.sum(v.astype(ld), dtype=ld) for v in cache['generation_energy_J'].values())
    energy = float(ld(displacement)+ld(conduction)+absorbed-sum(map(ld, increments))-sum(map(ld, outward)))
    fraction = cache.get('trap_fraction', old.trap_fraction)
    charge = float(Q*np.sum(model.vol.astype(ld)*(cache['p']-old.p_m3-cache['n']+old.n_m3-
                   model.Nt.astype(ld)*(fraction.astype(ld)-old.trap_fraction)), dtype=ld)+
                   dt*np.sum(qflux[boundary], dtype=ld))
    terminal_charge = dt*sum(float(-dq[f]/dt-qflux[f]) for f in model.bc)
    return max(abs(energy)/energy_atol_J, abs(charge)/charge_atol_C,
               abs(terminal_charge)/charge_atol_C)
