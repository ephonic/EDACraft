"""DD-adjudicated TFET temperature scaling (A7 cryo adjudication).

Golden: Sentaurus Hurkx cryo sweep of the calibrated TFET deck at
300/250/150/77 K (bench/sentaurus/calibration/tfet_cryo):
Ion(T)/Ion(300) = 1.000 / 0.965 / 0.916 / 0.913.
"""
import pytest

from tcad.search.tfet_frontier import (
    TfetFrontierConfig, _anchor_scale, _current_at, _temperature_scaling,
    REF_A_KANE, REF_EG_EV, REF_LAMBDA_NM, REF_MT, REF_ION_A_PER_UM,
    SS_DD_SCALE,
)


def test_a8_reanchor_to_sentaurus_golden():
    """A8: the compact anchor must be the Sentaurus deck measurement
    (2.786e-6 A/um), not the stale C++ DD replay (3.83e-4)."""
    assert REF_ION_A_PER_UM == pytest.approx(2.786e-6, rel=1e-3)


def test_a8_ss_scale_reproduces_sentaurus_reference():
    """Compact reference swing x SS_DD_SCALE = Sentaurus SS (185 mV/dec)."""
    x_ref = {
        "eg_t": REF_EG_EV, "lambda_nm": REF_LAMBDA_NM, "mt_ratio": REF_MT,
        "a_kane": REF_A_KANE, "vfb_offset": 0.0,
    }
    from tcad.search.tfet_frontier import evaluate_tfet_candidate
    c = evaluate_tfet_candidate(x_ref, TfetFrontierConfig(vdd=0.8))
    assert c.ss_avg_mV_per_dec == pytest.approx(185.0, rel=0.03)

DD_RATIO = {300.0: 1.000, 250.0: 0.965, 150.0: 0.916, 77.0: 0.913}


@pytest.mark.parametrize("t_k,ratio", sorted(DD_RATIO.items()))
def test_temperature_factor_matches_dd(t_k, ratio):
    assert _temperature_scaling(t_k) == pytest.approx(ratio, rel=0.01)


def test_no_naive_t32_boost_at_77k():
    """The corrected factor must NOT reproduce the old 7.69x boost."""
    assert _temperature_scaling(77.0) < 1.5


def test_clamped_outside_adjudicated_window():
    assert _temperature_scaling(4.0) == pytest.approx(_temperature_scaling(77.0))
    assert _temperature_scaling(500.0) == pytest.approx(_temperature_scaling(300.0))


def test_reference_ion_ratio_matches_dd():
    """Full compact model at the reference design must track DD ratios."""
    scale = _anchor_scale()
    x_ref = {
        "eg_t": REF_EG_EV, "lambda_nm": REF_LAMBDA_NM, "mt_ratio": REF_MT,
        "a_kane": REF_A_KANE, "vfb_offset": 0.0,
    }
    base = _current_at(0.8, x_ref, TfetFrontierConfig(temperature_K=300.0), scale)
    for t_k, ratio in DD_RATIO.items():
        ion = _current_at(0.8, x_ref, TfetFrontierConfig(temperature_K=t_k), scale)
        assert ion / base == pytest.approx(ratio, rel=0.01)
