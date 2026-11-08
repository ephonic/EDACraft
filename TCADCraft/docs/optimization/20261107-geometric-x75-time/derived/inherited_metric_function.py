def metrics(records):
    values = [sample_vectors(r, q) for r in records]
    assert values[0].keys() == values[1].keys() == values[2].keys()
    rows = {}
    failures = {}
    for name in values[0]:
        d01 = float(np.max(abs(values[1][name] - values[0][name])))
        d12 = float(np.max(abs(values[2][name] - values[1][name])))
        ratio = d12 / d01 if d01 > q['energy_roundoff_cutoff'] else None
        row = dict(normalized_d01=d01, normalized_d12=d12, increment_ratio=ratio)
        rows[name] = row
        if d12 >= q['energy_difference'] or (ratio is not None and ratio >= q['energy_ratio']):
            failures[name] = row
    return dict(metrics=rows, failures=failures, passed_metrics=len(rows) - len(failures), total_metrics=len(rows), difference_limit=q['energy_difference'], ratio_limit=q['energy_ratio'], roundoff_cutoff=q['energy_roundoff_cutoff'])
