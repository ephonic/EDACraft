"""A10 DD-adjudicated FeFET memory-window Ec correction.

Golden anchors (Sentaurus, bench/sentaurus/calibration/fefet_memory_window):
- golden design (t_fe=10nm, Ec=5e7):  bare MW 0.500 V -> DD 0.366 V (x0.73)
- A10 variant (t_fe=10nm, Ec=1.59e8): bare MW 1.177 V -> DD 0.016 V
  (window COLLAPSES: higher Ec pushes in-device switching further out of
  reach under series loading; bare formula predicts the opposite).
"""
import pytest

from tcad.search.fe_frontier import FeFrontierConfig, evaluate_fe_candidate

BASE = {
    "t_fe_nm": 10.0, "ps": 0.20, "ec": 5.0e7,
    "overdrive": 1.5, "tau0": 1e-8, "merz_exponent": 1.5, "vdd": 2.0,
    "trap_density_cm2": 1e11, "trap_capture_tau_s": 1e-3,
    "trap_emission_tau_s": 1e-1,
}


def _mw(x):
    r = evaluate_fe_candidate(x, FeFrontierConfig(), evaluator="analytic")
    assert r.trusted, r.violations
    return r.mw_V


def test_a10_golden_anchor():
    assert _mw(dict(BASE)) == pytest.approx(0.366, rel=0.01)


def test_a10_high_ec_collapse():
    x = dict(BASE, ps=0.421, ec=1.59e8, overdrive=1.37,
             merz_exponent=1.83)
    assert _mw(x) == pytest.approx(0.016, rel=0.15)


def test_a10_mw_monotone_decreasing_in_ec():
    lo = _mw(dict(BASE, ec=6e7))
    hi = _mw(dict(BASE, ec=1.2e8))
    assert hi < lo < _mw(dict(BASE))


def test_a10_factor_capped_at_one():
    # below the anchor Ec the correction never EXCEEDS the bare loop
    ec = 4.0e7
    r = evaluate_fe_candidate(dict(BASE, ec=ec),
                              FeFrontierConfig(), evaluator="analytic")
    bare = 2.0 * 10e-9 * (1.5 - 1.0) * ec
    assert r.mw_V <= bare * (1.0 + 1e-9)


def test_a11_thick_fe_collapse():
    """A11: t_fe 10->30 nm COLLAPSES the DD window to 0.039 V (Sentaurus,
    fefet_tfe30 deck) while the bare formula grows ~2x."""
    x = dict(BASE, t_fe_nm=30.0, overdrive=1.31)
    r = evaluate_fe_candidate(x, FeFrontierConfig(), evaluator="analytic")
    assert r.trusted, r.violations
    assert r.mw_V == pytest.approx(0.039, rel=0.05)


def test_mw_peaks_at_calibrated_design():
    """Neither knob direction improves the DD window (both collapse):
    the calibrated point is the DD optimum of this parameter space."""
    mw_ref = _mw(dict(BASE))
    for variant in (dict(BASE, ec=8e7), dict(BASE, ec=1.5e8),
                    dict(BASE, t_fe_nm=20.0), dict(BASE, t_fe_nm=5.0)):
        assert _mw(variant) < mw_ref
