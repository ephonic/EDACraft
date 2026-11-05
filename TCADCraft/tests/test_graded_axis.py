"""Independent geometry checks for graded native cell-centred coordinates."""
import numpy as np
import pytest

from tcad.mesh import graded_cell_centers


@pytest.mark.parametrize('cells,ratio', [
    (cells, ratio) for cells in (4, 8, 13, 32) for ratio in (.05, .15, .4)
    if cells != 32 or ratio != .4
])
@pytest.mark.parametrize('reverse', [False, True])
@pytest.mark.parametrize('scale', [1., 1e-9, 1e6])
def test_physical_span_and_pinned_width(cells, reverse, scale, ratio):
    lo, hi = -2 * scale, 3 * scale
    width = ratio * (hi - lo)
    x = graded_cell_centers(lo, hi, cells, boundary_cell_width=width, reverse=reverse)
    assert len(x) == cells
    assert np.all(np.diff(x) > 0)
    # Check physical support using the actual native boundary convention.
    np.testing.assert_allclose([x[0] - (x[1] - x[0]) / 2,
                               x[-1] + (x[-1] - x[-2]) / 2], [lo, hi],
                              atol=2e-14 * scale, rtol=0)
    at = -1 if reverse else 0
    boundary = hi if reverse else lo
    assert abs(x[at] - boundary) == pytest.approx(width / 2, rel=2e-12)
    # Recover interval widths independently from adjacent centre locations.
    faces = [lo]
    for point in x:
        faces.append(2 * point - faces[-1])
    widths = np.diff(faces)
    if reverse:
        widths = widths[::-1]
    np.testing.assert_allclose(widths[:2], width, rtol=1e-10)
    assert widths[-1] == pytest.approx(widths[-2], rel=1e-9)
    ratios = widths[2:-1] / widths[1:-2]
    np.testing.assert_allclose(ratios, ratios[0], rtol=1e-9)


@pytest.mark.parametrize('fine,coarse', [(12, 8), (16, 8), (24, 8)])
def test_joined_material_interface(fine, coarse):
    h = .4e-6 / fine
    a = (np.arange(fine) + .5) * h
    b = graded_cell_centers(.4e-6, .8e-6, coarse, boundary_cell_width=h)
    x = np.r_[a, b]
    assert (x[fine - 1] + x[fine]) / 2 == pytest.approx(.4e-6, rel=2e-15)
    assert x[0] - np.diff(x)[0] / 2 == pytest.approx(0, abs=1e-22)
    assert x[-1] + np.diff(x)[-1] / 2 == pytest.approx(.8e-6, rel=2e-15)


@pytest.mark.parametrize('scale', [1., 1e-9, 1e6])
@pytest.mark.parametrize('reverse', [False, True])
def test_extreme_grading_rejected_even_if_coordinates_are_increasing(scale, reverse):
    # Last widths would be ~1e-14 of the physical span. The initial code
    # accepted these monotone coordinates with percent-level spacing errors.
    with pytest.raises(ValueError, match='relative interval-width accuracy'):
        graded_cell_centers(-2 * scale, 3 * scale, 32,
                            boundary_cell_width=2 * scale, reverse=reverse)


@pytest.mark.parametrize('cells', [4, 8, 13, 32])
def test_uniform_limit(cells):
    x = graded_cell_centers(0., 1., cells, boundary_cell_width=1. / cells)
    np.testing.assert_allclose(x, (np.arange(cells) + .5) / cells, rtol=2e-14)


@pytest.mark.parametrize('lo,hi,width', [
    (1e308, 1.5e308, 1e306), (-2e-300, 3e-300, 1e-301),
])
def test_finite_extreme_scale_does_not_overflow_intermediate(lo, hi, width):
    with np.errstate(all='raise'):
        x = graded_cell_centers(lo, hi, 8, boundary_cell_width=width)
    assert np.isfinite(x).all()
    assert np.all(np.diff(x) > 0)


@pytest.mark.parametrize('kwargs', [
    dict(cells=3), dict(cells=True), dict(cells=4.), dict(cells=0),
    dict(start=1, stop=0), dict(stop=float('inf')), dict(start=float('nan')),
    dict(boundary_cell_width=0), dict(boundary_cell_width=-1),
    dict(boundary_cell_width=.5), dict(boundary_cell_width=1j),
    dict(boundary_cell_width=[.1]), dict(start=True), dict(reverse=1),
    dict(start='0'), dict(boundary_cell_width=None),
    dict(start=1e300, stop=np.nextafter(1e300, np.inf), boundary_cell_width=1e280),
])
def test_invalid_or_unrepresentable(kwargs):
    args = dict(start=0, stop=1, cells=8, boundary_cell_width=.1)
    args.update(kwargs)
    with pytest.raises(ValueError):
        graded_cell_centers(**args)
