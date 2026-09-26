"""Verification suite for the E1 FeFET frontier explorer (plan0918 E1).

Covers the analytic golden of each objective (play-loop crossings, exact
endurance inversion, exact Avrami switching time), the constraint trust gate,
NSGA-II vector mechanics, and (when the C++ core is importable) the
solver-vs-analytic memory-window consistency.
"""

import math

import numpy as np
import pytest

from tcad.physics.ferro_kinetics import (
    AvramiDomainSwitching,
    FieldHistoryCyclingState,
    simulate_kai_waveform,
)
from tcad.search.fe_frontier import (
    FeFrontierConfig,
    evaluate_fe_candidate,
    evolve_fe_frontier,
    _endurance_cycles,
    _loop_crossings,
    _non_dominated_fronts,
    _switch_time,
    _vec_dominates,
)


DESIGN = {
    "t_fe_nm": 20.0,
    "ps": 1.0,
    "ec": 2.0e8,
    "overdrive": 1.6,
    "tau0": 1.0e-9,
    "merz_exponent": 1.0,
}


class TestAnalyticObjectives:
    def test_memory_window_matches_play_crossing_formula(self):
        cand = evaluate_fe_candidate(DESIGN, evaluator="analytic")
        assert cand.trusted
        t_fe = DESIGN["t_fe_nm"] * 1e-9
        half = t_fe * DESIGN["ec"] * (DESIGN["overdrive"] - 1.0)
        # A10 DD adjudication factor (see test_fefet_mw_ec_dd.py): the
        # bare saturated-loop window is discounted for the series-loaded
        # in-device operation.
        a10 = min(0.73 * (5.0e7 / DESIGN["ec"]) ** 3.4
                  * (10.0 / DESIGN["t_fe_nm"]) ** 2.6, 1.0)
        assert cand.mw_V == pytest.approx(2.0 * half * a10, rel=1e-9)
        assert cand.vc_plus == pytest.approx(half, rel=1e-12)
        assert cand.vc_minus == pytest.approx(-half, rel=1e-12)

    def test_endurance_inversion_brackets_the_collapse_cycle(self):
        config = FeFrontierConfig()
        n_collapse, dev = _endurance_cycles(DESIGN, config)
        assert dev <= 1e-9
        e_prog = DESIGN["overdrive"] * DESIGN["ec"]

        def fraction(n):
            model = FieldHistoryCyclingState(
                wakeup_cycles=config.wakeup_cycles,
                fatigue_cycles=config.fatigue_cycles,
                wakeup_gain=config.wakeup_gain,
                fatigue_loss=config.fatigue_loss,
                reference_field=config.reference_field,
                fatigue_field_exponent=config.fatigue_field_exponent,
            )
            model.advance(float(n), e_prog)
            return model.active_fraction

        target = config.mw_floor_frac
        assert fraction(math.floor(n_collapse)) >= target
        assert fraction(math.ceil(n_collapse) + 1.0) < target

    def test_switch_time_matches_avrami_closed_form_and_waveform(self):
        config = FeFrontierConfig()
        t_closed = _switch_time(DESIGN, config)
        e_prog = DESIGN["overdrive"] * DESIGN["ec"]
        tau = DESIGN["tau0"] * (config.merz_field / e_prog) ** DESIGN["merz_exponent"]
        x_target = -math.log(1.0 - 0.999)
        expected = tau * x_target ** (1.0 / config.avrami_exponent)
        assert t_closed == pytest.approx(expected, rel=1e-12)

        # Cross-validate the closed form against the M4 waveform simulator.
        dt = t_closed / 64.0
        t = np.arange(65) * dt
        fields = np.full(65, e_prog)
        out = simulate_kai_waveform(
            t, fields, ps=DESIGN["ps"],
            domain_specs=[(1.0, {
                "avrami_exponent": config.avrami_exponent,
                "tau0": DESIGN["tau0"],
                "merz_field": config.merz_field,
                "merz_exponent": DESIGN["merz_exponent"],
                "onset_field": 0.0,
                "orientation": -1,
                "completion_fraction": 1.0 - 1e-15,
            })],
        )
        # P = Ps * orientation * (1 - 2f): at the completion fraction 0.999
        # the domain polarization reaches (2*0.999 - 1)*Ps = 0.998*Ps.
        assert out["polarization"][-1] == pytest.approx(0.998 * DESIGN["ps"], rel=1e-9)

    def test_objectives_vector_ordered(self):
        cand = evaluate_fe_candidate(DESIGN, evaluator="analytic")
        obj = cand.objectives
        assert obj.shape == (4,)
        assert np.all(np.isfinite(obj))
        assert obj[0] > 0.0


class TestConstraintGate:
    def test_breakdown_field_violation_rejects(self):
        bad = dict(DESIGN)
        bad["ec"] = 4.0e8
        bad["overdrive"] = 2.2
        cand = evaluate_fe_candidate(bad, evaluator="analytic")
        assert not cand.trusted
        assert any("E_bd" in v for v in cand.violations)
        assert np.all(cand.objectives == float("-inf"))

    def test_voltage_ceiling_rejects(self):
        bad = dict(DESIGN)
        bad["t_fe_nm"] = 40.0
        bad["ec"] = 2.5e8
        bad["overdrive"] = 2.2
        # E_prog = 5.5e8 < E_bd (no breakdown violation) but the program
        # voltage 22 V exceeds the 15 V ceiling.
        cand = evaluate_fe_candidate(bad, evaluator="analytic")
        assert not cand.trusted
        assert any("ceiling" in v for v in cand.violations)
        assert not any("E_bd" in v for v in cand.violations)

    def test_bounds_are_clipped(self):
        loose = dict(DESIGN)
        loose["t_fe_nm"] = 1.0e6
        cand = evaluate_fe_candidate(loose, evaluator="analytic")
        assert cand.x["t_fe_nm"] == pytest.approx(40.0)


class TestNsgaMechanics:
    def test_vec_dominance(self):
        a = np.array([2.0, 1.0, 0.5])
        b = np.array([1.0, 1.0, 0.5])
        assert _vec_dominates(a, b)
        assert not _vec_dominates(b, a)
        c = np.array([1.0, 2.0, 0.5])
        assert not _vec_dominates(a, c)
        assert not _vec_dominates(c, a)

    def test_front_detection(self):
        objectives = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.5, 0.5, 0.5],
            [0.4, 0.4, 0.4],
        ])
        fronts = _non_dominated_fronts(objectives)
        assert sorted(fronts[0]) == [0, 1, 2, 3]
        assert fronts[1] == [4]

    def test_loop_crossings_after_extremum(self):
        v = np.array([0.0, 2.0, 4.0, 2.0, 0.0, -2.0, -4.0, -2.0, 0.0, 2.0, 4.0])
        p = np.array([0.1, 0.5, 0.9, 0.5, 0.1, -0.4, -0.9, -0.5, -0.1, 0.4, 0.9])
        vc_descent, vc_ascent = _loop_crossings(v, p)
        # Descent crossing between (v=0, p=0.1) and (v=-2, p=-0.4).
        assert vc_descent == pytest.approx(-1.0)
        # Ascent crossing between (v=0, p=-0.1) and (v=2, p=0.4).
        assert vc_ascent == pytest.approx(1.0)


class TestEvolutionRun:
    def test_analytic_run_deterministic_and_front_nondominated(self):
        config = FeFrontierConfig()
        result_a = evolve_fe_frontier(
            config, population_size=10, generations=4, seed=42,
            evaluator="analytic",
        )
        result_b = evolve_fe_frontier(
            config, population_size=10, generations=4, seed=42,
            evaluator="analytic",
        )
        rows_a = result_a.to_rows()
        rows_b = result_b.to_rows()
        for ra, rb in zip(rows_a, rows_b):
            for key in ("t_fe_nm", "ps", "ec", "overdrive", "mw_V"):
                assert ra[key] == pytest.approx(rb[key], rel=1e-12, abs=1e-18)

        assert result_a.front, "front must contain trusted candidates"
        objectives = np.vstack([c.objectives for c in result_a.front])
        for i in range(len(objectives)):
            for j in range(len(objectives)):
                if i != j:
                    assert not _vec_dominates(objectives[j], objectives[i])

    def test_front_exhibits_mw_endurance_tradeoff(self):
        config = FeFrontierConfig()
        seeds = [
            {"t_fe_nm": 38.0, "ps": 1.3, "ec": 3.8e8, "overdrive": 1.4,
             "tau0": 1.0e-10, "merz_exponent": 1.5},
            {"t_fe_nm": 6.0, "ps": 0.15, "ec": 0.6e8, "overdrive": 2.1,
             "tau0": 5.0e-10, "merz_exponent": 0.8},
        ]
        result = evolve_fe_frontier(
            config, population_size=12, generations=5, seed=7,
            evaluator="analytic", init_population=seeds,
        )
        assert len(result.front) >= 2
        mw = np.array([c.mw_V for c in result.front])
        endurance = np.array([c.endurance_cycles for c in result.front])
        assert mw.max() / max(mw.min(), 1e-12) > 2.0
        # After the A10/A11 DD corrections the front clusters at low Ec
        # (high-Ec windows collapse), narrowing the endurance spread.
        assert endurance.max() / max(endurance.min(), 1e-12) > 2.0
        # The tradeoff is present when the best-MW front member does not also
        # hold the best endurance (MW and endurance are anti-correlated
        # through the program field: high overdrive widens the window and
        # accelerates M1 fatigue).
        best_mw_idx = int(np.argmax(mw))
        assert endurance[best_mw_idx] < endurance.max()

    def test_history_records_every_evaluation(self):
        result = evolve_fe_frontier(
            FeFrontierConfig(), population_size=8, generations=3, seed=1,
            evaluator="analytic",
        )
        assert len(result.history) == 8 * (3 + 1)


class TestSolverConsistency:
    def test_solver_memory_window_matches_analytic_play_formula(self):
        pytest.importorskip("tcad.core")
        config = FeFrontierConfig(slab_nodes=41, sweep_points_per_segment=24)
        cand = evaluate_fe_candidate(DESIGN, config, evaluator="solver")
        assert cand.trusted, cand.violations
        analytic = evaluate_fe_candidate(DESIGN, config, evaluator="analytic")
        t_fe = DESIGN["t_fe_nm"] * 1e-9
        sweep_res = t_fe * DESIGN["ec"] / config.sweep_points_per_segment
        assert cand.mw_V == pytest.approx(analytic.mw_V, abs=2.0 * sweep_res)
