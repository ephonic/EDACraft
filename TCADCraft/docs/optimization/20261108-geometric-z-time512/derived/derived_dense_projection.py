def dense_field_changes(records):
    axes = [np.asarray(records[0]['checkpoints'][0][k]) for k in ('x_m', 'y_m', 'z_m')]
    result = {}
    for phase in range(len(records[0]['checkpoints'])):
        fields = []
        for record in records:
            row = record['checkpoints'][phase]
            indices = []
            for key, axis in zip(('x_m', 'y_m', 'z_m'), axes):
                old = np.asarray(row[key])
                idx = np.searchsorted(old, axis)
                np.testing.assert_array_equal(old[idx], axis)
                indices.append(idx)
            ix, iy, iz = indices
            r = row['result']
            fields.append({key: np.asarray(r[key])[np.ix_(iy, ix)] for key in ('phi_V', 'Fn_eV', 'Fp_eV', 'trap_occupancy')})
            fields[-1]['dielectric_phi_V'] = np.asarray(r['dielectric_phi_V'])[np.ix_(iz, iy, ix)]
        for key in fields[0]:
            result[str(phase) + '_' + key] = [float(np.max(abs(b[key] - a[key]))) for a, b in zip(fields, fields[1:])]
    return dict(common_support_xyz=[len(a) for a in axes], absolute_field_increments=result, new_acceptance_gate=False)
