def check_linear_and_progress(s, record, linear, progress, ordering):
    count = record['steps_per_phase']
    expected_steps = 3 * count
    expected_records = expected_steps + 1
    assert len(linear) == expected_records and len(progress) == expected_steps
    rows = record['checkpoints']
    x, y, z = [np.asarray(rows[0][k]) for k in ('x_m', 'y_m', 'z_m')]
    selected = np.count_nonzero((z >= -2.5e-09) & (z <= 2.5e-09))
    s['linear_scope']['expected_dimension'] = int(len(x) * len(y) * len(z) - 2 * len(y) * (selected - 1))
    for i, stats in enumerate(linear):
        assert stats['factor_ordering'] == ordering
        s['linear_scope']['check_linear'](stats, i)
    for phase, row in enumerate(rows):
        s['equal'](row['result']['linear_solver_diagnostics'], linear[phase * count])
        if phase:
            s['equal'](row['previous']['linear_solver_diagnostics'], linear[phase * count - 1])
    for i, p in enumerate(progress, 1):
        assert p['phase'] == (i - 1) // count + 1 and p['step'] == (i - 1) % count + 1
        assert p['time_s'] == record['trace'][i]['time_s']
        assert np.isfinite(p['residual_scaled_linf']) and p['residual_scaled_linf'] <= 1e-12
        for k in ('linear_solves', 'factorizations'):
            assert p[k] == linear[i][k]
    return dict(expected_newton_dimension=s['linear_scope']['expected_dimension'], accepted_diagnostics=expected_records, linear_solves=sum((x['linear_solves'] for x in linear)), factorizations=sum((x['factorizations'] for x in linear)), gmres_iterations=sum((x['gmres_iterations'] for x in linear)), gmres_corrections=sum((x['gmres_corrections'] for x in linear)), refreshes=sum((x['refreshes'] for x in linear)))
