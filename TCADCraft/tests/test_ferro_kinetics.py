"""Verification suite for M1/M4 ferroelectric kinetics (plan0918 protocol).

Implements the solver-verification gates for the direction-1 work package:

* exact closed-form solutions (protocol 2.1),
* striding == explicit trajectory (protocol 2.3),
* degenerate limits to already-verified behaviour (protocol 2.5),
* structural invariants and monotonicity (protocol 2.2/2.6).
"""

import numpy as np
import pytest

from tcad.physics.ferro_kinetics import (
    AvramiDomainSwitching,
    FieldHistoryCyclingState,
    KaiMultiDomain,
    simulate_kai_waveform,
)


class TestFieldHistoryCyclingExactness:
    def test_two_segment_closed_form(self):
        model = FieldHistoryCyclingState(
            wakeup_cycles=100.0, fatigue_cycles=1000.0,
            wakeup_gain=0.0, fatigue_loss=0.0,
            reference_field=1.0e8, fatigue_field_exponent=2.0,
        )
        e1, e2 = 1.0e8, 2.0e8
        c1, c2 = 50.0, 30.0
        model.advance(c1, e1)
        model.advance(c2, e2)
        n_w1, n_w2 = 100.0, 100.0
        n_f1 = 1000.0 * (1.0e8 / e1) ** 2.0
        n_f2 = 1000.0 * (1.0e8 / e2) ** 2.0
        w_expected = 1.0 - np.exp(-c1 / n_w1) * np.exp(-c2 / n_w2)
        d_expected = 1.0 - np.exp(-c1 / n_f1) * np.exp(-c2 / n_f2)
        assert model.wakeup_state == pytest.approx(w_expected, rel=1e-14)
        assert model.fatigue_state == pytest.approx(d_expected, rel=1e-14)

    def test_field_history_order_invariance(self):
        forward = FieldHistoryCyclingState(
            wakeup_cycles=100.0, fatigue_cycles=1000.0,
            reference_field=1.0e8, fatigue_field_exponent=2.0,
        )
        backward = FieldHistoryCyclingState(
            wakeup_cycles=100.0, fatigue_cycles=1000.0,
            reference_field=1.0e8, fatigue_field_exponent=2.0,
        )
        forward.advance(10.0, 1.0e8)
        forward.advance(10.0, 3.0e8)
        backward.advance(10.0, 3.0e8)
        backward.advance(10.0, 1.0e8)
        assert forward.fatigue_state == pytest.approx(
            backward.fatigue_state, rel=1e-14, abs=1e-15,
        )
        assert forward.cycles == backward.cycles

    def test_striding_equals_explicit(self):
        strided = FieldHistoryCyclingState(
            wakeup_cycles=500.0, fatigue_cycles=2000.0,
            reference_field=1.0e8, fatigue_field_exponent=2.0,
            imprint_rate=0.01, imprint_field_max=1.0e6,
        )
        explicit = FieldHistoryCyclingState(
            wakeup_cycles=500.0, fatigue_cycles=2000.0,
            reference_field=1.0e8, fatigue_field_exponent=2.0,
            imprint_rate=0.01, imprint_field_max=1.0e6,
        )
        strided.advance_with_recheck(1000.0, 2.0e8, stride=250.0)
        for _ in range(1000):
            explicit.advance(1.0, 2.0e8)
        assert strided.wakeup_state == pytest.approx(
            explicit.wakeup_state, rel=1e-13, abs=1e-15,
        )
        assert strided.fatigue_state == pytest.approx(
            explicit.fatigue_state, rel=1e-13, abs=1e-15,
        )
        assert strided.imprint_state == pytest.approx(
            explicit.imprint_state, rel=1e-13, abs=1e-15,
        )
        assert strided.last_recheck_deviation <= 1e-13

    def test_subdivision_invariance(self):
        coarse = FieldHistoryCyclingState(
            wakeup_cycles=100.0, fatigue_cycles=1000.0,
            reference_field=1.0e8, fatigue_field_exponent=2.0,
        )
        fine = FieldHistoryCyclingState(
            wakeup_cycles=100.0, fatigue_cycles=1000.0,
            reference_field=1.0e8, fatigue_field_exponent=2.0,
        )
        coarse.advance(40.0, 2.0e8)
        for _ in range(40):
            fine.advance(1.0, 2.0e8)
        assert coarse.fatigue_state == pytest.approx(
            fine.fatigue_state, rel=1e-13, abs=1e-15,
        )


class TestFieldHistoryCyclingPhysics:
    def test_zero_field_freezes_damage(self):
        model = FieldHistoryCyclingState(
            wakeup_cycles=100.0, fatigue_cycles=1000.0,
            reference_field=1.0e8, fatigue_field_exponent=2.0,
        )
        model.advance(500.0, 1.0e8)
        frozen = (model.wakeup_state, model.fatigue_state, model.imprint_state)
        cycles_frozen = model.cycles
        model.advance(1.0e6, 0.0)
        assert (model.wakeup_state, model.fatigue_state, model.imprint_state) == frozen
        assert model.cycles == cycles_frozen

    def test_no_degradation_identity(self):
        model = FieldHistoryCyclingState(
            wakeup_gain=0.0, fatigue_loss=0.0,
        )
        for _ in range(20):
            model.advance(100.0, 5.0e8)
        assert model.active_fraction == 1.0

    def test_wakeup_then_fatigue_crossover(self):
        model = FieldHistoryCyclingState(
            wakeup_cycles=20.0, fatigue_cycles=2000.0,
            wakeup_gain=0.5, fatigue_loss=0.95,
            reference_field=1.0e8, fatigue_field_exponent=2.0,
        )
        fractions = []
        for _ in range(5000):
            fractions.append(model.advance(20.0, 1.0e8))
        assert max(fractions) > fractions[0]
        assert fractions[-1] < 0.5 * max(fractions)
        peak_idx = int(np.argmax(fractions))
        assert 0 < peak_idx < len(fractions) - 1

    def test_higher_field_accelerates_fatigue(self):
        mild = FieldHistoryCyclingState(
            fatigue_cycles=1000.0, reference_field=1.0e8,
            fatigue_field_exponent=2.0, wakeup_gain=0.0, fatigue_loss=1.0,
        )
        harsh = FieldHistoryCyclingState(
            fatigue_cycles=1000.0, reference_field=1.0e8,
            fatigue_field_exponent=2.0, wakeup_gain=0.0, fatigue_loss=1.0,
        )
        for _ in range(50):
            mild.advance(20.0, 1.0e8)
            harsh.advance(20.0, 2.0e8)
        assert harsh.fatigue_state > mild.fatigue_state

    def test_imprint_bounded_and_sign_tracking(self):
        model = FieldHistoryCyclingState(
            reference_field=1.0e8, imprint_rate=0.05,
            imprint_field_exponent=1.0, imprint_field_max=2.0e6,
        )
        for _ in range(500):
            model.advance(10.0, 1.0e8)
        assert model.imprint_state == pytest.approx(2.0e6, rel=1e-6)
        assert abs(model.imprint_state) <= 2.0e6
        for _ in range(500):
            model.advance(10.0, -1.0e8)
        assert model.imprint_state < 0.0
        assert abs(model.imprint_state) <= 2.0e6 + 1e-9

    def test_effective_field_adds_imprint(self):
        model = FieldHistoryCyclingState(
            reference_field=1.0e8, imprint_rate=0.5,
            imprint_field_max=1.0e6,
        )
        model.advance(50.0, 1.0e8)
        assert model.effective_field(0.0) == pytest.approx(model.imprint_state)
        assert model.effective_field(5.0e7) == pytest.approx(5.0e7 + model.imprint_state)


class TestAvramiExactness:
    def test_constant_field_closed_form_any_step_size(self):
        for n, steps in ((1.0, 1), (1.0, 7), (1.5, 13), (2.0, 4), (2.0, 64)):
            domain = AvramiDomainSwitching(
                avrami_exponent=n, tau0=2.0e-9, merz_field=1.0e8,
                merz_exponent=1.0, completion_fraction=1.0 - 1e-15,
            )
            e = 1.0e8
            tau = domain.tau(e)
            t_total = 5.0 * tau
            dt = t_total / steps
            for _ in range(steps):
                domain.advance(e, dt)
            expected = 1.0 - np.exp(-(t_total / tau) ** n)
            assert domain.switched_fraction == pytest.approx(
                expected, rel=1e-12, abs=1e-14,
            ), f"n={n}, steps={steps}"

    def test_n_equals_one_is_linear(self):
        domain = AvramiDomainSwitching(
            avrami_exponent=1.0, tau0=1.0e-9, merz_field=1.0e8,
            merz_exponent=0.0, completion_fraction=1.0 - 1e-15,
        )
        domain.progress = 0.25
        domain.advance(1.0e8, 1.0e-9)
        assert domain.progress == pytest.approx(0.25 + 1.0, rel=1e-14)

    def test_accumulate_update_is_exact_closed_form(self):
        domain = AvramiDomainSwitching(
            avrami_exponent=2.0, tau0=1.0e-9, merz_field=1.0e8,
            merz_exponent=1.0, completion_fraction=1.0 - 1e-15,
        )
        e = 2.0e8
        tau = domain.tau(e)
        domain.progress = 0.09
        root = 0.3
        domain.advance(e, 3.0 * tau)
        expected = (root + 3.0) ** 2.0
        assert domain.progress == pytest.approx(expected, rel=1e-14)

    def test_relaxation_exponential_in_root(self):
        domain = AvramiDomainSwitching(
            avrami_exponent=2.0, tau0=1.0e-9, merz_field=1.0e8,
            merz_exponent=0.0, completion_fraction=1.0 - 1e-15,
        )
        domain.progress = 0.16
        decay = np.exp(-4.0)
        for _ in range(4):
            domain.advance(0.0, 1.0e-9)
        assert domain.progress == pytest.approx((0.4 * decay) ** 2.0, rel=1e-13)


class TestAvramiPhysics:
    def test_tau_merz_monotone_decreasing(self):
        domain = AvramiDomainSwitching(merz_exponent=1.5)
        fields = np.linspace(5.0e7, 5.0e8, 9)
        taus = [domain.tau(e) for e in fields]
        assert all(taus[i] > taus[i + 1] for i in range(len(taus) - 1))

    def test_onset_threshold_blocks_progress(self):
        domain = AvramiDomainSwitching(
            onset_field=1.0e8, orientation=-1, completion_fraction=1.0 - 1e-15,
        )
        for _ in range(100):
            domain.advance(0.9e8, 1.0e-3)
        assert domain.progress == 0.0
        assert domain.switched_fraction == 0.0

    def test_instant_switch_limit(self):
        domain = AvramiDomainSwitching(
            tau0=1.0e-15, onset_field=1.0e6, merz_field=1.0e8,
            merz_exponent=1.0, orientation=-1,
        )
        domain.advance(1.0e8, 1.0e-9)
        assert domain.orientation == +1
        assert domain.progress == 0.0
        assert domain.polarization(1.0) == pytest.approx(1.0, rel=1e-9)

    def test_completion_flip_polarization_continuity(self):
        ps = 0.2
        completion = 0.9
        domain = AvramiDomainSwitching(
            avrami_exponent=1.0, tau0=1.0e-9, merz_field=1.0e8,
            merz_exponent=0.0, orientation=-1, completion_fraction=completion,
        )
        e = 1.0e8
        assert domain.tau(e) == pytest.approx(1.0e-9)
        domain.advance(e, 2.0e-9)
        assert domain.orientation == -1
        p_pre = domain.polarization(ps)
        x_flip = -np.log(1.0 - completion)
        domain.advance(e, (x_flip - 2.0) * 1.0e-9)
        assert domain.orientation == +1
        p_post = domain.polarization(ps)
        p_at_flip = ps * (2.0 * completion - 1.0)
        assert p_pre == pytest.approx(ps * (1.0 - 2.0 * np.exp(-2.0)), rel=1e-12)
        assert p_post == pytest.approx(ps, rel=1e-12)
        assert (p_at_flip - p_pre) == pytest.approx(
            ps * (2.0 * completion - 1.0 - (1.0 - 2.0 * np.exp(-2.0))), rel=1e-12,
        )
        assert (p_post - p_at_flip) == pytest.approx(
            2.0 * ps * (1.0 - completion), rel=1e-9,
        )

    def test_aligned_field_relaxes_partial_progress(self):
        domain = AvramiDomainSwitching(
            avrami_exponent=1.0, tau0=1.0e-9, merz_field=1.0e8,
            merz_exponent=0.0, orientation=+1, completion_fraction=1.0 - 1e-15,
        )
        domain.progress = 0.5
        domain.advance(1.0e8, 1.0e-9)
        assert domain.progress == pytest.approx(0.5 * np.exp(-1.0), rel=1e-14)


class TestKaiMultiDomain:
    def test_weights_must_sum_to_one(self):
        with pytest.raises(ValueError):
            KaiMultiDomain(
                ps=0.2, weights=[0.5, 0.6],
                domains=[AvramiDomainSwitching(), AvramiDomainSwitching()],
            )

    def test_polarization_bounded_under_random_sequence(self):
        rng = np.random.default_rng(20260918)
        ps = 0.25
        stack = KaiMultiDomain(
            ps=ps,
            weights=[0.5, 0.3, 0.2],
            domains=[
                AvramiDomainSwitching(
                    tau0=1e-9, onset_field=6.0e7, merz_field=1.0e8,
                    merz_exponent=1.2, avrami_exponent=1.5,
                    orientation=-1,
                ),
                AvramiDomainSwitching(
                    tau0=3e-9, onset_field=8.0e7, merz_field=1.0e8,
                    merz_exponent=1.0, avrami_exponent=1.0,
                    orientation=-1,
                ),
                AvramiDomainSwitching(
                    tau0=1e-8, onset_field=5.0e7, merz_field=1.0e8,
                    merz_exponent=0.8, avrami_exponent=2.0,
                    orientation=+1,
                ),
            ],
        )
        for _ in range(400):
            e = rng.uniform(-3.0e8, 3.0e8)
            stack.advance(e, rng.uniform(1e-10, 1e-7))
            p = stack.polarization()
            assert abs(p) <= ps * (1.0 + 1e-12)
            assert np.all(stack.switched_fractions() >= 0.0)
            assert np.all(stack.switched_fractions() <= 1.0)

    def test_identical_domains_reduce_to_single_domain(self):
        ps = 0.3
        single = AvramiDomainSwitching(
            avrami_exponent=1.5, tau0=1e-9, merz_field=1.0e8,
            merz_exponent=1.0, onset_field=5.0e7, orientation=-1,
        )
        stack = KaiMultiDomain(
            ps=ps, weights=[0.25, 0.25, 0.25, 0.25],
            domains=[
                AvramiDomainSwitching(
                    avrami_exponent=1.5, tau0=1e-9, merz_field=1.0e8,
                    merz_exponent=1.0, onset_field=5.0e7, orientation=-1,
                )
                for _ in range(4)
            ],
        )
        rng = np.random.default_rng(7)
        for _ in range(200):
            e = rng.uniform(-2.5e8, 2.5e8)
            dt = rng.uniform(1e-10, 1e-8)
            single.advance(e, dt)
            stack.advance(e, dt)
            assert stack.polarization() == pytest.approx(
                single.polarization(ps), rel=1e-12, abs=1e-14,
            )

    def test_waveform_simulation_runs_and_stays_physical(self):
        t = np.linspace(0.0, 2.0e-6, 2001)
        f = 2.0e8 * np.sign(np.sin(2.0 * np.pi * 1.0e6 * t))
        out = simulate_kai_waveform(
            t, f, ps=0.2,
            domain_specs=[
                (0.6, {"tau0": 1e-9, "avrami_exponent": 1.5, "onset_field": 5.0e7,
                       "orientation": -1}),
                (0.4, {"tau0": 5e-9, "avrami_exponent": 1.0, "onset_field": 6.0e7,
                       "orientation": -1}),
            ],
        )
        assert out["polarization"].shape == (t.size,)
        assert np.all(np.abs(out["polarization"]) <= 0.2 * (1.0 + 1e-12))
        assert np.all(out["switched_fractions"] >= 0.0)
        assert np.all(out["switched_fractions"] <= 1.0)

    def test_waveform_input_validation(self):
        with pytest.raises(ValueError):
            simulate_kai_waveform([0.0, 0.0], [0.0, 1.0e8], ps=0.2)
        with pytest.raises(ValueError):
            simulate_kai_waveform([0.0, 1.0], [np.nan, 1.0e8], ps=0.2)


class TestInterfaceCompatibility:
    def test_drop_in_for_endurance_driver_protocol(self):
        model = FieldHistoryCyclingState(
            wakeup_cycles=50.0, fatigue_cycles=500.0,
            wakeup_gain=0.2, fatigue_loss=0.5,
        )
        fraction = model.advance(1.0, 3.0e8)
        assert np.isfinite(fraction)
        assert hasattr(model, "wakeup_state")
        assert hasattr(model, "fatigue_state")
        assert 0.0 <= fraction <= 1.0 + model.wakeup_gain


class _FakeEnduranceSimulator:
    """Minimal simulator surface for run_endurance (no C++ dependency)."""

    class _Mesh:
        fields: dict = {}

        def npts(self):
            return 4

    def __init__(self):
        self.mesh = self._Mesh()
        self.contact_voltage = 0.0
        self.active_fraction_history = []
        self.builtin_field_history = []
        self.qot_history = []

    def update_contact(self, name, voltage):
        self.contact_voltage = float(voltage)

    def run(self, max_iter=50, tol=1e-10):
        return {}

    def set_ferroelectric_active_fraction(self, fraction):
        self.active_fraction_history.append(float(fraction))

    def set_ferroelectric_builtin_field(self, E_bi):
        self.builtin_field_history.append(float(E_bi))

    def set_oxide_traps(self, qot):
        self.qot_history.append(float(np.mean(qot)))


class TestEnduranceDriverIntegration:
    @staticmethod
    def _reference_sequence(model_cls, params, e_cycle, n_calls):
        reference = model_cls(**params)
        fractions = []
        imprints = []
        for k in range(n_calls):
            field = e_cycle if k % 2 == 0 else -e_cycle
            fractions.append(reference.advance(1.0, field))
            imprints.append(reference.imprint_field())
        return reference, fractions, imprints

    def test_per_half_cycle_advance_and_feedback(self):
        from tcad.postprocess.fe_loops import run_endurance

        params = dict(
            wakeup_cycles=4.0, fatigue_cycles=1.0e9,
            wakeup_gain=0.3, fatigue_loss=0.0,
            reference_field=1.0e8,
            imprint_rate=0.05, imprint_field_exponent=1.0,
            imprint_field_max=5.0e7,
        )
        model = FieldHistoryCyclingState(**params)
        sim = _FakeEnduranceSimulator()
        run_endurance(
            sim, "gate", V_pulse=1.0, fe_thickness=10e-9,
            n_cycles=4, measure_every=2,
            degradation_model=model, Q_ot_max=0.0,
        )
        e_cycle = 1.0 / 10e-9
        _, fractions, imprints = self._reference_sequence(
            FieldHistoryCyclingState, params, e_cycle, 8,
        )
        assert model.cycles == 8
        assert sim.active_fraction_history == pytest.approx(fractions)
        assert sim.builtin_field_history == pytest.approx([-b for b in imprints])
        assert all(abs(b) <= 5.0e7 for b in sim.builtin_field_history)

    def test_imprint_feedback_disabled_without_imprint_config(self):
        from tcad.postprocess.fe_loops import run_endurance

        model = FieldHistoryCyclingState(
            wakeup_cycles=4.0, fatigue_cycles=1.0e9,
            wakeup_gain=0.3, fatigue_loss=0.0,
        )
        sim = _FakeEnduranceSimulator()
        run_endurance(
            sim, "gate", V_pulse=1.0, fe_thickness=10e-9,
            n_cycles=2, measure_every=1,
            degradation_model=model, Q_ot_max=0.0,
        )
        assert sim.builtin_field_history == []

    def test_output_trajectories_reported(self):
        from tcad.postprocess.fe_loops import run_endurance

        model = FieldHistoryCyclingState(
            wakeup_cycles=2.0, fatigue_cycles=50.0,
            wakeup_gain=0.2, fatigue_loss=0.4,
            reference_field=1.0e8,
            imprint_rate=0.1, imprint_field_max=2.0e7,
        )
        sim = _FakeEnduranceSimulator()
        out = run_endurance(
            sim, "gate", V_pulse=1.0, fe_thickness=10e-9,
            n_cycles=4, measure_every=2,
            degradation_model=model, Q_ot_max=0.0,
        )
        assert out["imprint_field"].shape == (2,)
        assert np.all(np.isfinite(out["imprint_field"]))
        assert np.all(np.abs(out["imprint_field"]) <= 2.0e7)
        assert out["imprint_loop_shift_V"].shape == (2,)
        assert out["imprint_loop_shift_V"] == pytest.approx(
            -out["imprint_field"] * 10e-9,
        )
        assert out["active_fraction"].shape == (2,)
        assert "wakeup_state" in out and "fatigue_state" in out

    def test_unipolar_stress_imprint_grows_monotonically(self):
        model = FieldHistoryCyclingState(
            reference_field=1.0e8, imprint_rate=0.2,
            imprint_field_exponent=1.0, imprint_field_max=3.0e7,
        )
        values = [model.advance(1.0, 2.0e8) for _ in range(40)]
        imprint = model.imprint_field()
        assert imprint == pytest.approx(3.0e7, rel=1e-6)
        assert np.all(np.isfinite(values))

    def test_zero_field_half_cycle_freezes_state(self):
        model_a = FieldHistoryCyclingState(
            wakeup_cycles=4.0, fatigue_cycles=4.0,
            wakeup_gain=0.3, fatigue_loss=0.3,
        )
        model_a.advance(3.0, 2.0e8)
        frozen = model_a.wakeup_state
        model_a.advance(10.0, 0.0)
        assert model_a.wakeup_state == frozen
