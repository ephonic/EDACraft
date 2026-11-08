def describe(d01, d12, scale):
    resolved = min(d01, d12) / scale > q['energy_roundoff_cutoff']
    return dict(coarse_to_middle_absolute=d01, middle_to_fine_absolute=d12, normalized_coarse_to_middle=d01 / scale, normalized_middle_to_fine=d12 / scale, increment_ratio=d12 / d01 if resolved else None, observed_order=float(np.log2(d01 / d12)) if resolved else None, roundoff_resolved=resolved, decreasing=d12 < d01 if resolved else None)
