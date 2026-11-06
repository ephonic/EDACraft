def check_case(s, one, guard, r, linear, progress, case, artifacts=None, physics=True):
    g = geometry(case)
    count = case['steps_per_phase']
    steps = case['dynamic_steps']
    assert count == 128 and len(r['trace']) == steps + 1 and (len(r['checkpoints']) == case['checkpoints'])
    for row in r['checkpoints']:
        for k, a in zip(('x_m', 'y_m', 'z_m'), g):
            np.testing.assert_array_equal(row[k], a)
    assert all((x['factor_ordering'] == expected_ordering for x in linear))
    before = s['oracle']['checks']
    if case['mode'] == 'full':
        assert count == 128 and steps == 384 and (abs(r['trace'][-1]['time_s'] - 6e-11) < 1e-24)
        stats = guard(s, r, linear, progress, expected_ordering)
        ledger = one(s['geometry_lists'](deepcopy(r)), g[2], full_physics=physics, expected_count=count)
        result = dict(**stats, **ledger, full_pulse_completed=True)
    else:
        assert count == 128 and steps == 1 and (len(progress) == 1)
        q = progress[0]
        assert q['phase'] == q['step'] == 1 and q['time_s'] == 2e-11 / 128
        assert np.isfinite(q['residual_scaled_linf']) and q['residual_scaled_linf'] <= 1e-12
        for k in ('linear_solves', 'factorizations'):
            assert q[k] == linear[1][k]
        result = check_core(s, r, linear, g, physics=physics)
    if artifacts is not None:
        label = case['label']
        for phase, row in enumerate(r['checkpoints']):
            s['equal'](row, s['load'](artifacts / (label + '.checkpoint_' + str(phase))))
        journal = [json.loads(x) for x in (artifacts / (label + '.accepted_linear.jsonl')).read_text().splitlines()]
        assert [x['step'] for x in journal] == list(range(1, steps + 1))
        s['equal']([x['diagnostics'] for x in journal], linear[1:])
    result['independent_physics_and_ledger_checks'] = s['oracle']['checks'] - before
    return result
