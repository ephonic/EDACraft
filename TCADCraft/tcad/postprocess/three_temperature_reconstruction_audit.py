"""Independent adaptive-DOS reconstruction of the two face branches.

No native EOS, spectral, Poisson or reconstruction kernel is called. Conserved
storage and relaxation remain in the parent audit's mean-state thermodynamics.
"""
import numpy as np
from scipy.optimize import brentq
from tcad.mesh.finite_volume_reconstruction import cell_average_quadratic_coefficients
from .fermi_spectral_energy import reference_reservoir, reference_face


def reconstruct_reference_centers(model, new, mean_reservoirs):
    ld = np.longdouble
    edges = np.array(sorted(f.centroid_m[0] for f in model.mesh.faces if f.area_vector_m2[0] != 0), ld)
    xi = (np.asarray(model.mesh.centroids_m[:, 0], ld)-edges[:-1])/np.diff(edges)-ld('.5')
    def center(means, floor):
        co = cell_average_quadratic_coefficients(edges, means, lower_bound=floor)
        return co[:, 0]+co[:, 1]*xi+co[:, 2]*(xi*xi-ld(1)/12)
    lattice = center(model.capacity.astype(ld)*new.temperature_K, ld(model.capacity[0]))/model.capacity
    reservoirs = {}
    for s, density, temperature, band in (
        ('electrons', new.n_m3, new.electron_temperature_K, model.Ec),
        ('holes', new.p_m3, new.hole_temperature_K, model.Eh)):
        u = np.array([r['energy_density_J_m3'] for r in mean_reservoirs[s]], ld)
        n = center(density, 0); kinetic = center(u-band.astype(ld)*density, 0)
        rows = []
        for i in range(model.nc):
            # Decode kinetic energy directly at a zero common band. Independent
            # adaptive DOS integration, with a bracket covering the open domain.
            def residual(t):
                return float(reference_reservoir(n[i], t, 0., model.valleys[s])['energy_density_J_m3']/kinetic[i]-1)
            tc = brentq(residual, np.nextafter(1., 2.), np.nextafter(1e5, 0.), xtol=1e-10, rtol=2e-14)
            rows.append(reference_reservoir(n[i], tc, band[i], model.valleys[s]))
        reservoirs[s] = rows
    return reservoirs, lattice


def reference_reconstructed_face(model, s, f, low, one, two, high_one, high_two,
                                 new, a, b, reconstructed_lattice, base, exponent, z):
    ld = np.longdouble; q = z*ld('1.602176634e-19')
    face = model.mesh.faces[f]; i, j = face.owner, face.neighbor
    pn = b['cell_potential_V'][j] if j >= 0 else model.bc[f]
    mu_n = base[j]*(model.T/reconstructed_lattice[j])**exponent if j >= 0 else base[i]*(model.T/model.contacts[f].temperature_K)**exponent
    high = reference_face(high_one, high_two, model.valleys[s],
        phi_o=b['cell_potential_V'][i], phi_n=pn, phi_f=b['face_potential_V'][f], z=z,
        mu_o=base[i]*(model.T/reconstructed_lattice[i])**exponent, mu_n=mu_n,
        area=model.area[f], do=model.do[f], dn=model.dn[f] if j >= 0 else 0.,
        bulk_potential_path=model.bulk_potential_path)
    po = (ld(a['cell_potential_V'][i])+ld(b['cell_potential_V'][i]))/2
    pn = (ld(a['cell_potential_V'][j])+ld(b['cell_potential_V'][j]))/2 if j >= 0 else ld(model.bc[f])
    pf = (ld(a['face_potential_V'][f])+ld(b['face_potential_V'][f]))/2
    to, tn = ld(one['temperature_K']), ld(two['temperature_K'])
    af = (ld(one['chemical_potential_J'])+q*(po-pf))/to-(ld(two['chemical_potential_J'])+q*(pn-pf))/tn
    ag = 1/tn-1/to
    sigma = lambda row: af*ld(row['particle_flux_s'])+ag*ld(row['material_energy_flux_W'])
    sl, sh = sigma(low), sigma(high)
    if sl < 0:
        raise ValueError('independent midpoint-work baseline entropy is negative')
    theta = 1. if sh >= 0 else float(sl/(sl-sh))*(1-16*np.finfo(float).eps)
    def mixed(weight):
        out = {k:float((1-ld(weight))*ld(low[k])+ld(weight)*ld(high[k]))
               for k in ('particle_flux_s', 'material_energy_flux_W', 'total_energy_flux_W')}
        out['valley_moments'] = [dict(name=l['name'], **{k:float((1-ld(weight))*ld(l[k])+ld(weight)*ld(h[k]))
            for k in ('particle_flux_s', 'total_energy_flux_W')}) for l,h in zip(low['valley_moments'], high['valley_moments'])]
        return out
    out = mixed(theta)
    if sigma(out) < 0: theta = 0.; out = mixed(theta)
    out.update(entropy_production_W_K=float(sigma(out)), high_order_fraction=theta,
               low_order_face=low, reconstructed_face=high)
    return out


def check_reconstructed_face_report(row, target, particle_atol_s, energy_atol_W, entropy_atol_W_K):
    if (row.get('trace_closure') != 'convex_mixture_of_two_spectral_faces' or
        row.get('entropy_pairing_potential') != 'midpoint_work' or
        row.get('single_spectral_reservoir_pair') is not False or
        not np.isfinite(row.get('high_order_fraction', np.nan)) or
        not 0 <= row['high_order_fraction'] <= 1 or
        abs(row['high_order_fraction']-target['high_order_fraction']) > 1e-10):
        raise ValueError('reconstructed face descriptor or common weight mismatch')
    for name in ('low_order_face', 'reconstructed_face'):
        given, expected = row.get(name), target[name]
        if not isinstance(given, dict): raise ValueError('both spectral branch reports required')
        for key, tolerance in [('particle_flux_s', particle_atol_s), ('material_energy_flux_W', energy_atol_W),
                               ('total_energy_flux_W', energy_atol_W), ('entropy_production_W_K', entropy_atol_W_K)]:
            if not np.isfinite(given.get(key, np.nan)) or abs(given[key]-expected[key]) > tolerance:
                raise ValueError('independent spectral branch mismatch')
        if (given.get('statistics') != 'fermi_dirac' or given.get('execution_backend') != 'native' or
            given.get('trace_closure') != 'energy_resolved_nonthermal_occupations' or
            not 0 <= given['trace_occupation_min'] <= given['trace_occupation_max'] <= 1 or
            len(given.get('valley_moments', [])) != len(expected['valley_moments'])):
            raise ValueError('spectral branch trace or valley coverage mismatch')
        for g,e in zip(given['valley_moments'], expected['valley_moments']):
            if (g['name'] != e['name'] or not np.isfinite(g['particle_flux_s']) or not np.isfinite(g['total_energy_flux_W']) or abs(g['particle_flux_s']-e['particle_flux_s']) > particle_atol_s or abs(g['total_energy_flux_W']-e['total_energy_flux_W']) > energy_atol_W):
                raise ValueError('spectral branch valley moment mismatch')
