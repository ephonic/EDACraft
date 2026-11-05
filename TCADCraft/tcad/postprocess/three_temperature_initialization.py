"""Independent fixed-lattice stationary FD and external clamp-power audit."""
import numpy as np

from tcad.solver.cut_cell_transport import Q, _array
from tcad.solver.cut_cell_poisson import solve_cut_cell_poisson
from .fermi_spectral_energy import reference_reservoir, reference_face
from .three_temperature_energy import _reference_relaxation_times


def audit_lattice_clamped_state(model, initial, prepared, report, *, charge_atol_C,
                                particle_flux_atol_s, energy_power_atol_W, current_atol_A):
    """Rebuild all four stationary rows without production physical operators.

    The reported clamp is an instantaneous external power, not an energy
    integral or a solved lattice equation. An unchanged clock is required.
    """
    from tcad.solver.three_temperature_initialization import _validate_configuration, SCOPE
    _validate_configuration(model, initial); model._validate_state(prepared)
    for value in (charge_atol_C, particle_flux_atol_s, energy_power_atol_W, current_atol_A):
        _array(value, 1, 'stationary audit budget', positive=True)
    nc = model.nc; nf = len(model.mesh.faces); ld = np.longdouble
    valid = (report.get('scope') == SCOPE and report.get('carrier_steady_state') is True
        and report.get('lattice_temperature_clamped') is True
        and report.get('lattice_energy_equation_solved') is False
        and report.get('clock_advanced') is False and report.get('complete_device_energy') is False
        and report.get('physical_validated') is False
        and report.get('bulk_potential_path') == model.bulk_potential_path
        and prepared.time_s == initial.time_s
        and np.array_equal(prepared.temperature_K, initial.temperature_K)
        and np.array_equal(prepared.trap_fraction, initial.trap_fraction))
    for key in ('integrated_particle_flux_s', 'integrated_carrier_energy_flux_W',
                'cell_particle_residual_s', 'cell_carrier_energy_residual_W'):
        valid = valid and set(report[key]) == {'electrons', 'holes'}
    poisson = solve_cut_cell_poisson(model.mesh, model.eps,
        model.rhofix.astype(ld)+Q*(prepared.p_m3-prepared.n_m3),
        dirichlet_V=model.bc, charge_atol_C=charge_atol_C)
    valid = valid and poisson['valid']
    phi = poisson['cell_potential_V']; phif = poisson['face_potential_V']
    reported_poisson = report['poisson']
    valid = (valid and np.max(abs(phi-_array(reported_poisson['cell_potential_V'], nc, 'potential'))) <= 1e-11
        and np.max(abs(phif-_array(reported_poisson['face_potential_V'], nf, 'face potential'))) <= 1e-11)
    carrier_rows = {}; divergences = {}; rates = {}; energies = {}; exchanges = {}
    flux_errors = []; energy_errors = []; row_errors = []; particle_row_errors = []
    work = np.zeros(nc, ld); minimum_entropy = 0.
    active = set(map(int, model.internal)) | set(map(int, model.contact_faces))
    for s, density, temperature, band, mobility, exponent, z, tau, law in (
        ('electrons', prepared.n_m3, prepared.electron_temperature_K, model.Ec, model.mn, model.mn_exponent, -1,
         model.tau_n, model.relaxation_laws[0]),
        ('holes', prepared.p_m3, prepared.hole_temperature_K, model.Eh, model.mp, model.mp_exponent, 1,
         model.tau_p, model.relaxation_laws[1])):
        reservoir = [reference_reservoir(density[i], temperature[i], band[i], model.valleys[s]) for i in range(nc)]
        equilibrium = [reference_reservoir(density[i], prepared.temperature_K[i], band[i], model.valleys[s]) for i in range(nc)]
        flux = np.zeros(nf); energy = np.zeros(nf)
        for f in active:
            face = model.mesh.faces[f]; i, j = face.owner, face.neighbor
            area = np.linalg.norm(face.area_vector_m2); normal = face.area_vector_m2/area
            do = (face.centroid_m-model.mesh.centroids_m[i]) @ normal
            if j >= 0:
                other = reservoir[j]; potential = phi[j]
                dn = (model.mesh.centroids_m[j]-face.centroid_m) @ normal
                mu = mobility[j]*(model.T/prepared.temperature_K[j])**exponent
            else:
                contact = model.contacts[f]
                other = reference_reservoir(contact.n_m3 if s == 'electrons' else contact.p_m3,
                    contact.temperature_K, band[i], model.valleys[s])
                potential = model.bc[f]; dn = 0.
                mu = mobility[i]*(model.T/contact.temperature_K)**exponent
            moment = reference_face(reservoir[i], other, model.valleys[s], phi_o=phi[i], phi_n=potential,
                phi_f=phif[f], z=z, mu_o=mobility[i]*(model.T/prepared.temperature_K[i])**exponent,
                mu_n=mu, area=area, do=do, dn=dn, A=model.emission[s].get(f),
                bulk_potential_path=model.bulk_potential_path)
            flux[f] = moment['particle_flux_s']; energy[f] = moment['material_energy_flux_W']
            minimum_entropy = min(minimum_entropy, moment['entropy_production_W_K'])
        effective_tau = np.asarray(tau, ld) if law is None else _reference_relaxation_times(
            tau, density, temperature, prepared.temperature_K, law)
        exchange = model.vol.astype(ld)*np.array([ld(a['energy_density_J_m3'])-ld(b['energy_density_J_m3'])
            for a, b in zip(reservoir, equilibrium)], ld)/effective_tau
        divergence = model.mesh.divergence_integrals(flux)
        qflux = z*Q*flux
        electrical = phi*model.mesh.divergence_integrals(qflux)-model.mesh.divergence_integrals(phif*qflux)
        row = model.mesh.divergence_integrals(energy).astype(ld)+exchange-electrical
        carrier_rows[s] = row; divergences[s] = divergence; rates[s] = flux; energies[s] = energy; exchanges[s] = exchange
        work += electrical
        flux_errors.append(float(np.max(abs(flux-_array(report['integrated_particle_flux_s'][s], nf, 'particle flux')))))
        energy_errors.append(float(np.max(abs(energy-_array(report['integrated_carrier_energy_flux_W'][s], nf, 'carrier power')))))
        row_errors.append(float(np.max(abs(row-_array(report['cell_carrier_energy_residual_W'][s], nc, 'energy row')))))
        particle_row_errors.append(float(np.max(abs(divergence-_array(report['cell_particle_residual_s'][s], nc, 'particle row')))))
    transfer = model.vol.astype(ld)*model.intercarrier_conductance_W_m3_K*(
        prepared.electron_temperature_K.astype(ld)-prepared.hole_temperature_K)
    carrier_rows['electrons'] += transfer; carrier_rows['holes'] -= transfer
    # Compare complete rows again after the optional intercarrier transfer.
    row_errors = [float(np.max(abs(carrier_rows[s]-_array(report['cell_carrier_energy_residual_W'][s], nc, 'energy row'))))
                  for s in carrier_rows]
    heat = np.zeros(nf)
    for f, face in enumerate(model.mesh.faces):
        i, j = face.owner, face.neighbor; area = np.linalg.norm(face.area_vector_m2)
        normal = face.area_vector_m2/area; do = (face.centroid_m-model.mesh.centroids_m[i]) @ normal
        if j >= 0:
            dn = (model.mesh.centroids_m[j]-face.centroid_m) @ normal
            heat[f] = area/(do/model.conductivity[i]+dn/model.conductivity[j])*(prepared.temperature_K[i]-prepared.temperature_K[j])
        elif f in model.bath:
            heat[f] = area*model.conductivity[i]/do*(prepared.temperature_K[i]-model.bath[f])
    clamp = model.mesh.divergence_integrals(heat).astype(ld)-exchanges['electrons']-exchanges['holes']
    clamp_error = float(np.max(abs(clamp-_array(report['cell_clamp_heat_input_W'], nc, 'external clamp power'))))
    maximum_particle = max(float(np.max(abs(v))) for v in divergences.values())
    maximum_energy = max(float(np.max(abs(v))) for v in carrier_rows.values())
    current = float(Q*np.sum(divergences['holes'].astype(ld)-divergences['electrons'], dtype=ld))
    boundary = [f for f, face in enumerate(model.mesh.faces) if face.neighbor < 0]
    energy_balance = float(np.sum(work+clamp, dtype=ld)-np.sum(
        (energies['electrons'].astype(ld)+energies['holes']+heat)[boundary], dtype=ld))
    valid = (valid and maximum_particle <= particle_flux_atol_s and maximum_energy <= energy_power_atol_W
        and abs(current) <= current_atol_A and abs(energy_balance) <= energy_power_atol_W
        and max(flux_errors+particle_row_errors) <= particle_flux_atol_s
        and max(energy_errors+row_errors+[clamp_error]) <= energy_power_atol_W
        and minimum_entropy >= -1e-19)
    return dict(valid=bool(valid), maximum_particle_residual_s=maximum_particle,
        maximum_carrier_energy_residual_W=maximum_energy, terminal_current_residual_A=current,
        external_clamp_energy_balance_residual_W=energy_balance,
        maximum_constitutive_particle_error_s=max(flux_errors),
        maximum_constitutive_energy_error_W=max(energy_errors),
        maximum_reported_energy_row_error_W=max(row_errors), maximum_clamp_power_error_W=clamp_error,
        total_external_clamp_heat_input_W=float(np.sum(clamp, dtype=ld)),
        lattice_energy_equation_solved=False, complete_device_energy=False, physical_validated=False)
