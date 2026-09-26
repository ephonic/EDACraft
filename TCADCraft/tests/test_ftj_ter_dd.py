"""A12 DD-adjudicated FTJ barrier-modulation efficiency.

Golden: Sentaurus NLM tunneling through n+Si/HfO2-FE(2nm)/n+Si
(bench/sentaurus/calibration/ftj_a12), program +-1.5 V, read +0.1 V:
TER = 2.609e-12 / 4.487e-13 = 5.8 for the frontier design
(Ps=0.46, eg0=0.91 eV, delta=0.63 eV, mt=0.23).
The compact's unscreened barrier modulation predicted ~1e8.
"""
import math
import pytest

from tcad.search.ftj_frontier import evaluate_ftj, FtjConfig

FRONTIER = {
    "t_fe_nm": 2.0, "ps": 0.46, "eg0_eV": 0.91,
    "delta_eV": 0.63, "mt_ratio": 0.23, "a_kane": 6.5e20,
}


def test_a12_frontier_ter_matches_dd():
    c = evaluate_ftj(FRONTIER, FtjConfig())
    assert c.trusted, c.violations
    assert c.ter == pytest.approx(5.8, rel=0.05)


def test_a12_no_eight_order_ter_claims_remain():
    """With the screening efficiency applied, the WKB artifact regime
    (TER ~ 1e8) is unreachable for physical delta values."""
    for delta in (0.1, 0.4, 0.8):
        c = evaluate_ftj({**FRONTIER, "delta_eV": delta}, FtjConfig())
        assert c.trusted
        assert c.ter < 1.0e3


def test_ter_monotone_in_delta():
    t0 = evaluate_ftj({**FRONTIER, "delta_eV": 0.2}, FtjConfig()).ter
    t1 = evaluate_ftj({**FRONTIER, "delta_eV": 0.6}, FtjConfig()).ter
    assert t1 > t0
