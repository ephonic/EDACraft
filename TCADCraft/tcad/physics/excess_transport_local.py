"""Native local carrier-energy Schur complement, without a device step.

The caller must provide matched DOS equilibrium energies and physical oriented
face/source moments. A nonzero lattice or particle row remains an outer solve's
responsibility. No carrier temperature is inferred from an unresolved excess.
See src/three_temperature_excess_local.h for the decimal input schema.
"""

FIELDS = ('particle_n','particle_p','excess_n_J_m3','excess_p_J_m3',
          'storage_n_J','storage_p_J','storage_l_J','exchange_n_J','exchange_p_J',
          'work_n_J','work_p_J','residual_n_J','residual_p_J','residual_l_J',
          'tau_n_s','tau_p_s','retained_n','retained_p','drive_n_J_m3','drive_p_J_m3')
SCOPE = 'prescribed_moments_b0_local_carrier_energy_Schur_complement'


def assemble_excess_transport_local(cells, faces, timestep):
    """Return decimal rows; no acceptance, state commit or hidden fallback."""
    from tcad.core._bindings import native_three_temperature_excess_local_raw
    c=tuple(tuple(row) for row in cells);f=tuple(tuple(row) for row in faces)
    if not c or any(len(row)!=34 for row in c) or any(len(row)!=13 for row in f):
        raise ValueError('explicit 34-column cells and 13-column faces required')
    raw=native_three_temperature_excess_local_raw(
        [v for row in c for v in row],[v for row in f for v in row],timestep)
    nc=len(c);nf=len(f)
    if len(raw)!=20*nc+nf:raise ValueError('native excess local output coverage mismatch')
    return dict(scope=SCOPE,cells=[dict(zip(FIELDS,raw[20*i:20*(i+1)])) for i in range(nc)],
        heat_flux_W=raw[20*nc:],device_state_advanced=False,complete_device_energy=False,
        physical_validated=False,nonlinear_face_coupling_solved=False)
