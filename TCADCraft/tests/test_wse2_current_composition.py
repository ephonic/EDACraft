"""Independent Decimal references for WSe2 current composition and limiting."""
from decimal import Decimal, localcontext
import math
import sys

import pytest

from tcad.physics.contact import WSe2CompactContactModel, WSe2TransportWindow, WSe2TwoWindowTransferModel


def make(electron, hole, coupling=0., floor=None):
    def window(value):
        return WSe2TransportWindow(center_gate_V=0., width_V=1.,
            peak_current_A_per_um=value, floor_current_A_per_um=value, drain_exponent=0.)
    return WSe2TwoWindowTransferModel(window(electron), window(hole),
        valley_floor_A_per_um=min(electron, hole) if floor is None else floor,
        component_coupling=coupling)


def reference(electron, hole, coupling, floor):
    with localcontext() as ctx:
        ctx.prec = 1600
        d = Decimal.from_float
        coupled = d(coupling) * (d(electron) * d(hole)).sqrt()
        total = d(electron) + d(hole) + coupled + d(floor)
        return dict(electron_A_per_um=electron, hole_A_per_um=hole,
            coupled_A_per_um=float(coupled), floor_A_per_um=floor,
            total_A_per_um=float(total))


PAIRS = [(math.ulp(0.), math.ulp(0.)), (1e-320, 1e-320), (1e-200, 1e-200),
    (1e-300, 1e300), (1e-200, 1e100), (1e-9, 1e-12),
    (1e100, 1e100), (1e300, 1e300), (1e308, 1e308),
    (math.ulp(0.), 1e300), (sys.float_info.min, 1e-300), (1., math.ulp(0.))]


@pytest.mark.parametrize('electron,hole', PAIRS)
@pytest.mark.parametrize('coupling', [0., .5, 1e-100, 1e100])
def test_composition_preserves_physical_components_across_float_range(electron, hole, coupling):
    model = make(electron, hole, coupling)
    expected = reference(electron, hole, coupling, model.valley_floor_A_per_um)
    if (coupling > 0. and expected['coupled_A_per_um'] == 0.) or any(
            not math.isfinite(value) for value in expected.values()):
        with pytest.raises(ValueError, match='representable'):
            model.components_A_per_um(0., .5, 300.)
        if math.isfinite(expected['total_A_per_um']):
            assert model.abs_current_A_per_um(0., .5, 300.) == pytest.approx(
                expected['total_A_per_um'], rel=3e-15, abs=2 * math.ulp(expected['total_A_per_um']))
        else:
            with pytest.raises(ValueError, match='representable'):
                model.abs_current_A_per_um(0., .5, 300.)
        return
    result = model.components_A_per_um(0., .5, 300.)
    for name, value in result.items():
        assert value == pytest.approx(expected[name], rel=3e-15, abs=2 * math.ulp(expected[name]))
    assert result['total_A_per_um'] == math.fsum(value for name, value in result.items()
                                               if name != 'total_A_per_um')
    assert model.abs_current_A_per_um(0., .5, 300.) == result['total_A_per_um']
    if coupling == 0.:
        assert result['coupled_A_per_um'] == 0.


@pytest.mark.parametrize('electron,hole', [(1e-200, 1e-200), (1e300, 1e-300),
    (math.ulp(0.), 1e300), (1e-9, 1e-12)])
def test_electron_hole_exchange_preserves_coupling_and_total(electron, hole):
    first = make(electron, hole, .5).components_A_per_um(0., .5, 300.)
    second = make(hole, electron, .5).components_A_per_um(0., .5, 300.)
    assert first['coupled_A_per_um'] == second['coupled_A_per_um']
    assert first['total_A_per_um'] == second['total_A_per_um']


@pytest.mark.parametrize('current', [0., math.ulp(0.), 1e-300, 1., 1e300])
@pytest.mark.parametrize('limit', [math.ulp(0.), 1e-300, 1., 1e100])
def test_enabled_limiter_matches_independent_harmonic_current(current, limit):
    model = WSe2CompactContactModel(electron_current_limit_A_per_um=limit)
    with localcontext() as ctx:
        ctx.prec = 1600
        d = Decimal.from_float
        expected = float(d(current) * d(limit) / (d(current) + d(limit)))
    if current > 0. and expected == 0.:
        with pytest.raises(ValueError, match='representable'):
            model.electron_current_limit(current)
    else:
        actual = model.electron_current_limit(current)
        assert actual == pytest.approx(expected, rel=3e-15, abs=math.ulp(expected))
        assert 0. <= actual <= min(current, limit)


@pytest.mark.parametrize('limit', [1e299, 1e300])
@pytest.mark.parametrize('current', [0., math.ulp(0.), 1., sys.float_info.max])
def test_existing_limiter_disable_threshold_is_preserved(limit, current):
    assert WSe2CompactContactModel(electron_current_limit_A_per_um=limit).electron_current_limit(current) == current


@pytest.mark.parametrize('limit', [1., 1e300])
@pytest.mark.parametrize('current', [-1., math.nan, math.inf, -math.inf])
def test_limiter_rejects_invalid_current_even_when_disabled(limit, current):
    with pytest.raises(ValueError, match='finite|>= 0'):
        WSe2CompactContactModel(electron_current_limit_A_per_um=limit).electron_current_limit(current)


@pytest.mark.parametrize('bad', [math.nan, math.inf])
def test_nonfinite_window_output_is_rejected_before_combination(bad):
    class InvalidWindow:
        def current_A_per_um(self, *_args):
            return bad
    model = WSe2TwoWindowTransferModel(InvalidWindow(), make(1., 1.).hole_window)
    with pytest.raises(ValueError, match='finite'):
        model.components_A_per_um(0., .5, 300.)
