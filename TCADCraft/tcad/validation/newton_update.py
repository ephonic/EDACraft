"""Check additive Newton snapshot transitions in declared common raw units.

This conditional observation audit checks after = before + exported_update.
It cannot assign a NewtonPlot update to an iteration or a solve epoch by its
filename; the caller must establish consecutive states in the same solve.
No solver, convergence or commercial alignment qualification is granted.
"""
from decimal import Decimal, localcontext

if __package__:
    from .hfs_gqf import binary64_rounding_cell
else:
    from hfs_gqf import binary64_rounding_cell


def audit_newton_update_transition(before, after, updates):
    """Audit finite binary64 observations and expose unresolvable small updates.

    All three sequences must use identical raw units and node order. Exported
    updates must already include damping; multiplying by a fitted factor is
    outside the contract. Closed rounding cells conserve both tie possibilities.
    Compatibility is an existence check in the observation cells, not proof of
    the unrounded internal state or of temporal association. A compatible update
    whose magnitude is below node spacing is explicitly marked sub_resolution.
    Invalid input returns valid=False; ambiguous observations never establish a
    resolved transition. Empty/mismatched observations are rejected.
    """
    result = dict(valid=False, compatible=False, observations=0, consistent=0,
                  inconsistent=0, sub_resolution=0, resolved_consistent=0,
                  nodes=[], errors=[], chronology_proven=False,
                  convergence_qualified=False, commercial_alignment_qualified=False)
    try:
        if any(isinstance(x, (str, bytes)) for x in (before, after, updates)):
            raise ValueError('three numeric observation sequences required')
        arrays = [list(x) for x in (before, after, updates)]
        if not arrays[0] or len({len(x) for x in arrays}) != 1:
            raise ValueError('nonempty observations of equal length required')
        cells = [[binary64_rounding_cell(x) for x in row] for row in arrays]
        with localcontext() as ctx:
            # Covers exact sums from the binary64 subnormal range through
            # near-maximum finite values, without a context-rounding pad.
            ctx.prec = 1700
            for i, (b, a, u) in enumerate(zip(*cells)):
                expected = b[0]+u[0], b[1]+u[1]
                compatible = expected[0] <= a[1] and a[0] <= expected[1]
                gap = max(Decimal(0), a[0]-expected[1], expected[0]-a[1])
                # The widths of observation cells are local raw node spacing.
                # Use the narrower endpoint cell for a conservative label.
                spacing = min(b[1]-b[0], a[1]-a[0])
                sub = max(x.copy_abs() for x in u) < spacing
                result['nodes'].append(dict(node=i,compatible=compatible,
                    sub_resolution=sub,raw_interval_gap=str(gap),
                    expected_after_interval=[str(x) for x in expected],
                    observed_after_interval=[str(x) for x in a]))
                result['consistent'] += int(compatible)
                result['inconsistent'] += int(not compatible)
                result['sub_resolution'] += int(sub)
                result['resolved_consistent'] += int(compatible and not sub)
        result.update(valid=True, observations=len(arrays[0]),
                      compatible=result['inconsistent'] == 0)
    except (TypeError, ValueError) as exc:
        result['errors'].append(str(exc))
    return result
