def audit_one(rec, expected_z, full_physics=True):
    checkpoint_count = 0
    trace_count = 0
    contact = rec['contact']
    dielectric = rec['dielectric']
    level = rec['level']
    count = rec['steps_per_phase']
    family = rec['mesh_family']
    assert contact in ('linear', 'thermionic') and type(dielectric) is bool
    assert contact == 'thermionic' and family == 'space' and (level == 3) and (count == 128) and (rec['phase_s'] == policy['energy_phase_s'])
    assert dielectric is True and rec['boundary'] == 'finite_side_electrodes_5nm_v1'
    assert rec['contact_z_bounds_m'] == [[-2.5e-09, 2.5e-09]] * 2
    checkpoints = rec['checkpoints']
    trace = rec['trace']
    dt = rec['phase_s'] / count
    assert len(checkpoints) == 4 and len(trace) == 3 * count + 1
    nx = (8 if family == 'space' else 4) * 2 ** level + 1
    ny = (1 if family == 'space' else 2) * 2 ** level + 1
    u = np.linspace(0.0, 1.0, nx)
    x = 1e-07 * (1 - np.cos(np.pi * u)) if family == 'space' else 2e-07 * u ** 4 / (u ** 4 + (1 - u) ** 4)
    y = np.linspace(0.0, 1e-07, ny)
    yy, xx = np.meshgrid(y / 1e-07, x / 2e-07, indexing='ij')
    for phase, row in enumerate(checkpoints):
        assert row['contact'] == contact and row['x_m'] == x.tolist() and (row['y_m'] == y.tolist())
        mat = row['material']
        cfg = row['traps']
        r = row['result']
        assert row['contact_z_bounds_m'] == r['contact_z_bounds_m'] == rec['contact_z_bounds_m']
        assert mat == dict(name='MoS2 sheet' if contact == 'thermionic' else 'Graphene sheet', dispersion='parabolic' if contact == 'thermionic' else 'dirac', gap_eV=1.8 if contact == 'thermionic' else 0.0, reference_eV=-0.9 if contact == 'thermionic' else 0.0, mass_n_m0=0.5, mass_p_m0=0.6, degeneracy_n=4.0, degeneracy_p=2.0 if contact == 'thermionic' else 4.0, fermi_velocity_m_s=1000000.0)
        assert row['source_V'] == row['fermi_offset_eV'] == row['equilibrium_fermi_eV'] == 0.0
        assert row['drain_V'] == (0.0 if phase == 0 else 0.003)
        assert row['initial_occupancy'] == 'equilibrium' and row['equilibrium_hold'] is False
        assert row['mobility_n_m2_Vs'] == 0.02 and row['mobility_p_m2_Vs'] == 0.01 and (row['temperature_K'] == 300.0)
        assert row['sheet_permittivity_F'] == 0.0 and (not np.any(row['doping_m2'])) and (not np.any(row['fixed_charge_C_m2']))
        assert r['transport_scheme'] == 'diffusion_enhanced'
        assert cfg['kind'] == ('donor' if contact == 'thermionic' else 'acceptor')
        assert cfg['capture_n_m2_s'] == 2e-06 and cfg['capture_p_m2_s'] == 1e-06
        for k, expected in (('density_m2', 100000000000000.0 * (1 + 0.2 * xx + 0.1 * yy)), ('energy_offset_eV', (mat['gap_eV'] / 2 - 0.04 if contact == 'thermionic' else 0.01) + 0.003 * (xx - yy)), ('degeneracy', 1.5 + 0.3 * yy)):
            np.testing.assert_array_equal(cfg[k], expected)
        vg = 0.005 + 0.002 * np.cos(np.pi * xx) * np.cos(np.pi * yy) + (0.0, 0.03, -0.02, 0.01)[phase]
        if dielectric:
            assert row['z_m'] == expected_z.tolist()
            assert row['sheet_index'] == len(expected_z) // 2 and np.all(np.array(row['permittivity_F_m']) == 5 * 8.8541878128e-12)
            np.testing.assert_array_equal(row['top_gate_V'], vg)
            assert not np.any(row['bottom_gate_V'])
        else:
            np.testing.assert_array_equal(row['gate_V'], vg)
            assert np.all(np.array(row['capacitance_F_m2']) == 0.006)
        if contact == 'linear':
            assert np.all(np.array(row['contact_resistance_ohm_m']) == 0.003)
        else:
            assert np.all(np.array(row['thermionic_barrier_n_eV']) == 0.12)
        assert r['accepted'] and r['converged']
        gate('energy_observation_time', abs(r['time_s'] - phase * rec['phase_s']), 1e-24)
        i = phase * count
        for state, scalar in ((r, trace[i]),) + (((row['previous'], trace[i - 1]),) if phase else ()):
            for key in ('time_s', 'sheet_charge_C', 'trap_charge_C', 'untrapped_sheet_charge_C', 'contact_charge_C', 'sheet_contact_charge_C', 'dielectric_contact_charge_C', 'dielectric_energy_J'):
                assert state[key] == scalar[key], key
            assert scalar['gates'] == {k: state[k + '_charge_C'] for k in scalar['gates']}
        if phase:
            assert row['dt_s'] == dt
            assert trace[i]['conduction'] == r['terminal_currents_into_sheet_A'] and trace[i]['total'] == r['terminal_total_currents_A']
            assert 'trap_initialization' not in r and 'trap_equilibrium_fermi_eV' not in r
        if full_physics:
            audit(row)
        checkpoint_count += 1
    integral = 0.0
    trap_integral = 0.0
    free_integral = 0.0
    for i, s in enumerate(trace):
        charges = [s['sheet_charge_C'], *s['contact_charge_C'].values(), *s['gates'].values()]
        cscale = max(max(map(abs, charges)), 1e-20)
        for name in ('source', 'drain'):
            gate('trace_contact_split', abs(s['contact_charge_C'][name] - s['sheet_contact_charge_C'][name] - s['dielectric_contact_charge_C'][name]) / cscale, policy['flux_relative'])
        assert s['dielectric_energy_J'] >= 0.0
        gate('energy_trace_Gauss', abs(sum(charges)) / cscale, policy['gauss_scaled'])
        gate('energy_trace_charge_split', abs(s['sheet_charge_C'] - s['trap_charge_C'] - s['untrapped_sheet_charge_C']) / cscale, 1e-12)
        if not i:
            assert s['time_s'] == 0.0
            continue
        old = trace[i - 1]
        assert s['dt_s'] == dt and s['phase'] == (i - 1) // count + 1
        assert s['time_s'] == old['time_s'] + dt
        assert set(s['conduction']) == {'source', 'drain'} and set(s['total']) == {'source', 'drain', *s['gates']}
        qrate = (s['sheet_charge_C'] - old['sheet_charge_C']) / dt
        cscale = max(max(map(abs, s['conduction'].values())), max(map(abs, s['total'].values())), abs(qrate), 1e-12)
        gate('energy_trace_conduction_KCL', abs(sum(s['conduction'].values()) - qrate) / cscale, policy['terminal_total_KCL_relative'])
        gate('energy_trace_total_KCL', abs(sum(s['total'].values())) / cscale, policy['terminal_total_KCL_relative'])
        for key in s['total']:
            expected = s['conduction'].get(key, 0.0)
            category = 'contact_charge_C' if key in ('source', 'drain') else 'gates'
            expected += (s[category][key] - old[category][key]) / dt
            gate('energy_trace_displacement', abs(s['total'][key] - expected) / cscale, policy['terminal_total_KCL_relative'])
        for rate, key in (('trap_charge_rate_A', 'trap_charge_C'), ('free_carrier_charge_rate_A', 'untrapped_sheet_charge_C')):
            expected = (s[key] - old[key]) / dt
            gate('energy_trace_storage', abs(s[rate] - expected) / cscale, policy['terminal_total_KCL_relative'])
        integral += sum(s['conduction'].values()) * dt
        trap_integral += s['trap_charge_rate_A'] * dt
        free_integral += s['free_carrier_charge_rate_A'] * dt
        trace_count += 1
    for name, total, key in (('conduction', integral, 'sheet_charge_C'), ('trap', trap_integral, 'trap_charge_C'), ('free', free_integral, 'untrapped_sheet_charge_C')):
        gate('energy_integrated_' + name, abs(total - (trace[-1][key] - trace[0][key])) / policy['energy_charge_scale_C'], policy['terminal_total_KCL_relative'])
    gate('energy_nonzero_pulse', 0.0001 / max(float(np.max(abs(np.array(checkpoints[1]['result']['trap_occupancy']) - np.array(checkpoints[0]['result']['trap_occupancy'])))), 1e-100), 1.0)
    assert abs(checkpoints[3]['result']['terminal_currents_into_sheet_A']['drain']) > 1e-12
    return dict(checkpoints=checkpoint_count, steps=trace_count)
