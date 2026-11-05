"""Independent channel limits and complete multi-state error accounting."""
import math

import numpy as np
import pytest

from tcad.search.level_placement import LevelPlacementConfig, evaluate_placement, _gaps_to_positions
from tcad.search.mlc_frontier import MlcFrontierConfig, evaluate_mlc_candidate


def test_three_state_loss_has_complete_coded_metrics():
    cfg = LevelPlacementConfig(n_levels=3, total_budget=4, n_chain=8,
                               lam0_per_s=0, mu0_per_s=1, t_retention_s=math.log(2))
    result = evaluate_placement(np.zeros(2), cfg)
    expected = np.array([[1,0,0], [1/4,3/4,0], [1/16,10/16,5/16]])
    assert result.symbol_error_rate == pytest.approx(5/16, abs=1e-14)
    assert result.bit_error_rate == pytest.approx(1/6, abs=1e-14)
    np.testing.assert_allclose(result.readout["confusion_matrix"], expected, atol=1e-14)
    assert result.ber_worst == pytest.approx(11/32)  # Kept as a separate binary-pair diagnostic.
    assert result.worst_bit_error == pytest.approx(3/8)
    assert result.effective_bits == result.mutual_information_bits
    assert result.readout["codewords"] == ["00", "01", "11"]
    assert result.readout["unused_codewords"] == 1


def test_erased_four_state_channel_has_zero_information():
    cfg = LevelPlacementConfig(n_levels=4, total_budget=6, n_chain=8,
                               lam0_per_s=0, mu0_per_s=1, t_retention_s=100)
    result = evaluate_placement(np.zeros(3), cfg)
    assert result.effective_bits < 1e-30
    assert result.symbol_error_rate == pytest.approx(0.75, abs=1e-12)
    assert result.bit_error_rate == pytest.approx(0.5, abs=1e-12)
    assert result.effective_bits < 1e-30
    assert result.mutual_information_bits < 1e-30


def test_finite_candidate_rejected_when_numerical_domain_is_too_small():
    cfg = LevelPlacementConfig(n_levels=2, total_budget=10, n_chain=10,
                               lam0_per_s=1, mu0_per_s=0, t_retention_s=1)
    result = evaluate_placement(np.zeros(1), cfg)
    assert math.isfinite(result.ber_worst)
    assert not result.trusted
    assert not result.validation["numerical_valid"]
    assert result.validation["max_domain_escape_probability"] == pytest.approx(1-math.exp(-1))


def test_e3_integer_threshold_assigns_tie_to_upper_symbol():
    cfg = MlcFrontierConfig(lam0=0, mu0=1, t_retention=math.log(2),
                           spacing=(2,2), stress_scale=(1,1))
    result = evaluate_mlc_candidate({"spacing":2,"stress_scale":1}, 2, cfg)
    # Upper state n=4: P(n<3)=11/16, including n=2. Lower n=2 never crosses 3.
    assert result.worst_pair_error == pytest.approx(11/16, abs=1e-14)
    assert result.bit_error_rate == pytest.approx(11/32, abs=1e-14)
    assert result.validation["decision_boundaries"] == [3]


def test_e3_integer_threshold_counts_capture_ties():
    cfg = MlcFrontierConfig(lam0=1, mu0=0, t_retention=1,
                           spacing=(2,2), stress_scale=(1,1))
    result = evaluate_mlc_candidate({"spacing":2,"stress_scale":1},2,cfg)
    # Lower n=2 is decoded high after its first capture at n=3.
    assert result.worst_pair_error == pytest.approx(1-math.exp(-1), abs=1e-14)
    assert result.bit_error_rate == pytest.approx(0.5*(1-math.exp(-1)), abs=1e-14)


def test_zero_retention_is_noiseless_and_information_matches_entropy():
    cfg = LevelPlacementConfig(n_levels=4, total_budget=6, n_chain=8,
                               t_retention_s=0, priors=(0.5,0.25,0.125,0.125))
    result = evaluate_placement(np.zeros(3), cfg)
    assert result.trusted
    assert result.bit_error_rate == 0
    assert result.symbol_error_rate == 0
    assert result.mutual_information_bits == pytest.approx(1.75)
    assert result.improvement_factor == 1


@pytest.mark.parametrize("logits", [np.array([float("nan")]), np.array([float("inf")])])
def test_nonfinite_gap_design_is_not_clipped_into_validity(logits):
    with pytest.raises(ValueError):
        evaluate_placement(logits, LevelPlacementConfig(n_levels=2, total_budget=4))


def test_binary_pure_loss_matches_known_ber():
    from tcad.physics.storage_readout import electron_storage_readout
    result, evidence = electron_storage_readout([0,1], 4, 0, 1, 1)
    assert result.bit_error_rate == pytest.approx(0.5*(1-math.exp(-1)), rel=1e-12)
    assert result.symbol_error_rate == result.bit_error_rate
    assert evidence["domain_escape_probability_by_written"] == [0,0]


def test_nonadjacent_misclassification_contributes_hamming_cost():
    from tcad.physics.storage_readout import channel_metrics
    result = channel_metrics([[1,0,0], [0,1,0], [1,0,0]])
    assert result.symbol_error_rate == pytest.approx(1/3)
    assert result.bit_error_rate == pytest.approx(1/3)  # 11 -> 00 flips two of two bits.


def test_gray_and_binary_codes_change_ber_but_not_channel_information():
    from tcad.physics.storage_readout import channel_metrics
    confusion = [[1,0,0], [0,0.75,0.25], [0,0.25,0.75]]
    gray = channel_metrics(confusion)
    binary = channel_metrics(confusion, codes=("00","01","10"))
    assert gray.bit_error_rate == pytest.approx(1/12)
    assert binary.bit_error_rate == pytest.approx(1/6)
    assert gray.symbol_error_rate == binary.symbol_error_rate
    assert gray.mutual_information_bits == binary.mutual_information_bits


def test_asymmetric_channel_and_prior_match_closed_form():
    from tcad.physics.storage_readout import channel_metrics
    entropy = lambda p: -p*math.log2(p)-(1-p)*math.log2(1-p)
    result = channel_metrics([[0.9,0.1],[0.4,0.6]], priors=[0.8,0.2])
    assert result.symbol_error_rate == pytest.approx(0.16)
    assert result.bit_error_rate == pytest.approx(0.16)
    assert result.mutual_information_bits == pytest.approx(entropy(0.2)-0.8*entropy(0.1)-0.2*entropy(0.6))


def test_fixed_output_has_no_information():
    from tcad.physics.storage_readout import channel_metrics
    result = channel_metrics([[1,0],[1,0]], priors=[0.3,0.7])
    assert result.mutual_information_bits == pytest.approx(0, abs=1e-15)
    assert result.bit_error_rate == pytest.approx(0.7)


def test_zero_prior_and_output_masses_are_supported():
    from tcad.physics.storage_readout import channel_metrics
    result = channel_metrics([[1,0],[0,1]], priors=[1,0])
    assert result.mutual_information_bits == 0
    assert result.input_entropy_bits == 0
    assert result.bit_error_rate == 0


def test_tiny_error_is_summed_without_success_subtraction():
    from tcad.physics.storage_readout import channel_metrics
    result = channel_metrics([[1,1e-18],[0,1]])
    assert result.bit_error_rate == pytest.approx(5e-19, rel=1e-12, abs=0)
    assert result.symbol_error_rate == pytest.approx(5e-19, rel=1e-12, abs=0)


@pytest.mark.parametrize("confusion", [
    [[1,0],[0,0.9]], [[1,0],[0,float("nan")]], [[1,0],[-0.1,1.1]],
    [[1,0,0],[0,1,0]], [[1]],
])
def test_invalid_confusion_rejected(confusion):
    from tcad.physics.storage_readout import channel_metrics
    with pytest.raises(ValueError):
        channel_metrics(confusion)


@pytest.mark.parametrize("priors", [[1,1], [0.5,-0.5], [0.2], [float("nan"),0.5]])
def test_invalid_priors_rejected(priors):
    from tcad.physics.storage_readout import channel_metrics
    with pytest.raises(ValueError):
        channel_metrics(np.eye(2), priors=priors)


@pytest.mark.parametrize("codes", [("0","0"),("0","11"),("0","2"),("0",),(0,1)])
def test_invalid_codewords_rejected(codes):
    from tcad.physics.storage_readout import channel_metrics
    with pytest.raises(ValueError):
        channel_metrics(np.eye(2), codes=codes)


def test_code_padding_changes_bit_length_not_mutual_information():
    from tcad.physics.storage_readout import channel_metrics
    narrow = channel_metrics([[0.9,0.1],[0.2,0.8]])
    wide = channel_metrics([[0.9,0.1],[0.2,0.8]], codes=("000","001"))
    assert wide.bit_error_rate == pytest.approx(narrow.bit_error_rate/3)
    assert wide.mutual_information_bits == narrow.mutual_information_bits
    assert wide.as_dict()["code_bits"] == 3
    assert wide.as_dict()["unused_codewords"] == 6


def test_integer_and_half_integer_thresholds_use_same_tie_rule():
    from tcad.physics.storage_readout import decode_distributions
    probability = [[0,1,0],[0,0,1]]
    at_integer = decode_distributions(probability, [1])
    at_half = decode_distributions(probability, [0.5])
    assert at_integer.confusion_matrix.tolist() == at_half.confusion_matrix.tolist() == [[0,1],[0,1]]


@pytest.mark.parametrize("thresholds", [[0],[3],[float("nan")], [1,2]])
def test_invalid_decoder_bins_rejected(thresholds):
    from tcad.physics.storage_readout import decode_distributions
    with pytest.raises(ValueError):
        decode_distributions([[1,0,0],[0,0,1]], thresholds)


def test_duplicate_integer_bins_rejected():
    from tcad.physics.storage_readout import decode_distributions
    with pytest.raises(ValueError):
        decode_distributions(np.eye(3), [0.2,0.7])


def test_program_quantization_precedes_threshold_selection():
    from tcad.search.level_placement import _evaluate_positions
    cfg = LevelPlacementConfig(n_levels=3, total_budget=6, n_chain=8, t_retention_s=0)
    result, evidence, _ = _evaluate_positions(np.array([0,2.9,5.4]), cfg)
    assert evidence["programmed_counts"] == [0,3,5]
    assert evidence["decision_boundaries"] == [2,4]
    assert result.bit_error_rate == 0


def test_domain_escape_audit_catches_paths_that_returned():
    from tcad.physics.storage_readout import electron_storage_readout, _retained_count
    result, evidence = electron_storage_readout([0,4], 4, 2, 100, 0.1)
    distribution, _ = _retained_count(4,4,2,100,0.1,False)
    assert evidence["max_domain_escape_probability"] > 1e4*distribution[-1]
    assert not evidence["numerical_valid"]
    assert math.isfinite(result.bit_error_rate)


def test_headroom_and_physical_capacity_are_distinct_declared_models():
    from tcad.physics.storage_readout import electron_storage_readout
    _, numerical = electron_storage_readout([0,4], 12, 0.01, 0, 1)
    _, physical = electron_storage_readout([0,4], 4, 1, 0, 1, numerical_upper_boundary=False)
    assert numerical["numerical_valid"] and physical["numerical_valid"]
    assert numerical["upper_boundary"] != physical["upper_boundary"]
    assert not physical["physical_validated"]


def test_cached_probabilities_are_not_mutated_by_public_readout():
    from tcad.physics.storage_readout import electron_storage_readout
    first, _ = electron_storage_readout([0,2], 4, 0, 1, 1)
    expected = first.confusion_matrix.copy()
    first.confusion_matrix[:] = 0
    second, _ = electron_storage_readout([0,2], 4, 0, 1, 1)
    np.testing.assert_array_equal(second.confusion_matrix, expected)


def test_rate_changes_do_not_reuse_a_stale_cached_distribution():
    cfg = LevelPlacementConfig(n_levels=2, total_budget=4, n_chain=8,
                               lam0_per_s=0, mu0_per_s=1, t_retention_s=1)
    disturbed = evaluate_placement(np.zeros(1), cfg)
    cfg.t_retention_s = 0
    noiseless = evaluate_placement(np.zeros(1), cfg)
    assert disturbed.bit_error_rate > 0
    assert noiseless.bit_error_rate == 0


def test_custom_e3_prior_and_codes_are_applied():
    cfg = MlcFrontierConfig(levels_choices=(2,), spacing=(2,2), stress_scale=(1,1),
                           mu0=1, lam0=0, t_retention=math.log(2),
                           priors_by_levels={2:(0.75,0.25)}, codewords_by_levels={2:("000","001")})
    result = evaluate_mlc_candidate({"spacing":2,"stress_scale":1},2,cfg)
    assert result.symbol_error_rate == pytest.approx(11/64)
    assert result.bit_error_rate == pytest.approx(11/192)
    assert result.readout["code_bits"] == 3
    assert result.bits <= result.readout["input_entropy_bits"]


def test_nonpower_of_two_e3_alphabet_is_explicitly_coded():
    cfg = MlcFrontierConfig(levels_choices=(3,), spacing=(1,1), stress_scale=(1,1),
                           mu0=1, lam0=0, t_retention=math.log(2))
    result = evaluate_mlc_candidate({"spacing":1,"stress_scale":1},3,cfg)
    assert result.trusted
    assert result.bit_error_rate == pytest.approx(17/48)
    assert result.readout["unused_codewords"] == 1


def test_invalid_e3_design_does_not_pass_finite_only_gate():
    result = evaluate_mlc_candidate({"spacing":float("nan"),"stress_scale":0.5},2)
    assert not result.trusted
    assert result.violations
    result = evaluate_mlc_candidate({"spacing":0.2,"stress_scale":1},4,
                                    MlcFrontierConfig(spacing=(0.2,0.2)))
    assert not result.trusted  # Programming collapses multiple symbols to one count.


@pytest.mark.parametrize("name", ["spacing", "stress_scale"])
@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan")])
def test_e3_nonfinite_raw_input_is_rejected_before_clipping(name, value):
    design = {"spacing": 2, "stress_scale": 0.5, name: value}
    candidate = evaluate_mlc_candidate(design, 2)
    assert not candidate.trusted
    assert candidate.violations == ["non-finite design input"]


@pytest.mark.parametrize("parameter,value", [
    ("mu0_per_s",-1), ("lam0_per_s",float("nan")), ("t_retention_s",-1),
    ("n_levels",1), ("total_budget",2.5), ("overflow_tolerance",-1),
])
def test_invalid_placement_config_rejected(parameter,value):
    with pytest.raises(ValueError):
        LevelPlacementConfig(**{parameter:value})


def test_unvalidated_rates_cannot_become_physical_evidence():
    result = evaluate_placement(np.zeros(3), LevelPlacementConfig())
    assert result.trusted
    assert result.validation["rate_source"] == "unvalidated_default_proxy"
    assert not result.validation["physical_validated"]
    assert "numerical" in result.validation["trust_scope"]
    assert "not_capacity" in result.readout["information_scope"]


def test_wrong_logit_count_and_insufficient_spacing_budget_rejected():
    with pytest.raises(ValueError):
        _gaps_to_positions(np.zeros(1),4,3)
    with pytest.raises(ValueError):
        _gaps_to_positions(np.zeros(3),2,4)


def test_placement_channel_matches_independent_generator_and_decode():
    from scipy.linalg import expm
    cfg = LevelPlacementConfig(n_levels=3,total_budget=8,n_chain=14,
                               lam0_per_s=0.2,mu0_per_s=0.3,t_retention_s=2)
    # Integer placements cover the admissible interior range for this search.
    n = cfg.n_chain + 1
    generator = np.zeros((n,n))
    for state in range(n):
        if state < n-1:
            generator[state+1,state] = cfg.lam0_per_s
        if state > 0:
            generator[state-1,state] = cfg.mu0_per_s*state
        generator[state,state] = -generator[:,state].sum()
    transition = expm(generator*cfg.t_retention_s)
    for middle in range(2,7):
        logits = np.log(np.array([middle-1.5,8-middle-1.5]))
        candidate = evaluate_placement(logits,cfg)
        counts = [0,middle,8]
        boundaries = [math.ceil(middle/2),math.ceil((middle+8)/2)]
        confusion = np.array([[transition[:boundaries[0],initial].sum(),
                               transition[boundaries[0]:boundaries[1],initial].sum(),
                               transition[boundaries[1]:,initial].sum()] for initial in counts])
        # Fixed Gray words 00,01,11 give this independently written distance matrix.
        distances = np.array([[0,1,2],[1,0,1],[2,1,0]])
        expected_ber = float((confusion*distances).sum()/6)
        assert candidate.bit_error_rate == pytest.approx(expected_ber,rel=2e-12)
        np.testing.assert_allclose(candidate.readout["confusion_matrix"],confusion,atol=2e-13)


@pytest.mark.parametrize("kwargs", [{"numerical_upper_boundary":"False"},
                                    {"overflow_tolerance":2}, {"capture_rate":-1}])
def test_domain_options_cannot_silently_change_model(kwargs):
    from tcad.physics.storage_readout import electron_storage_readout
    options=dict(counts=[0,2],n_max=4,capture_rate=0,loss_rate=1,duration=1)
    options.update(kwargs)
    with pytest.raises(ValueError):
        electron_storage_readout(**options)
