"""Verification suite for the M5 NC dual-verdict model (plan0918 protocol)."""

import math

import numpy as np
import pytest

from tcad.physics.nc_verdict import (
    LKCircuitModel,
    measure_dip,
    nc_verdict,
    run_triangular_sweep,
)


FE_MODEL = LKCircuitModel(
    alpha=-5.0e8, beta=1.5e9, gamma=1.0e3,
    epsilon_r=20.0, thickness=10.0e-9, area=1.0e-12, rs=50.0,
)


class TestModelValidation:
    def test_ps_and_ec_closed_forms(self):
        m = FE_MODEL
        ps = math.sqrt(5.0e8 / 1.5e9)
        assert m.ps() == pytest.approx(ps, rel=1e-12)
        ec = (2.0 / 3.0) * 5.0e8 * math.sqrt(5.0e8 / (3.0 * 1.5e9))
        assert m.ec_static() == pytest.approx(ec, rel=1e-12)

    def test_s_curve_has_negative_slope_branch(self):
        m = FE_MODEL
        p = np.linspace(-m.ps(), m.ps(), 101)
        e = m.static_field(p)
        slope = np.diff(e) / np.diff(p)
        assert np.any(slope < 0.0), "static NC branch must exist for alpha<0"

    def test_input_validation(self):
        with pytest.raises(ValueError):
            LKCircuitModel(beta=-1.0)
        with pytest.raises(ValueError):
            LKCircuitModel(gamma=0.0)
        with pytest.raises(ValueError):
            LKCircuitModel(rs=-1.0)


class TestLinearDielectricLimit:
    def test_pure_capacitor_current_follows_ramp(self):
        # Freeze the LK channel (gamma -> large): P stays at zero and the
        # device is a linear capacitor, I = C dV/dt away from ramp corners.
        # (alpha = beta = 0 with finite gamma would make P a free integrator,
        # which is NOT the linear-dielectric limit of the LK equation.)
        m = LKCircuitModel(alpha=0.0, beta=0.0, gamma=1.0e12, rs=50.0)
        period = 1.0e-6
        n = 20000
        sweep = run_triangular_sweep(m, v_max=1.0, period=period, n_steps=n)
        c = m.capacitance
        quarter = n // 4
        expected = c * 1.0 / (period / 4.0)
        interior = sweep["I"][100: quarter - 100]
        assert np.allclose(interior, expected, rtol=2e-2)
        assert np.max(np.abs(sweep["P"])) < 1e-9

    def test_no_dip_for_linear_capacitor(self):
        m = LKCircuitModel(alpha=0.0, beta=0.0, gamma=1.0e12, rs=50.0)
        sweep = run_triangular_sweep(m, v_max=1.0, period=1.0e-6, n_steps=8000)
        assert measure_dip(sweep) < 1e-6


class TestQuasiStaticBranch:
    def test_ideal_slow_ramp_matches_static_s_curve(self):
        m = LKCircuitModel(
            **{**FE_MODEL.__dict__, "rs": 0.0, "gamma": 1.0e3},
        )
        v_max = 2.0 * m.ec_static() * m.thickness * 1.2
        sweep = run_triangular_sweep(m, v_max=v_max, period=1.0e-3, n_steps=40000)
        p = sweep["P"]
        v_fe = sweep["V_fe"]
        # On the monotone branches (|P| > 0.6 Ps, away from the switching
        # traverse) the quasi-static relation V_fe = d*(alpha P + beta P^3)
        # must hold pointwise.
        # Exclude the switching traverse: mid-switch points satisfy
        # |P| > 0.6 Ps while the field has already swung past the spinodal,
        # so the branch relation legitimately does not hold there.  Keep
        # only settled-branch points (small |dP/dt|).
        dpdt = np.gradient(p, sweep["t"])
        mask = (np.abs(p) > 0.6 * m.ps()) & (np.abs(dpdt) < 0.05 * m.ps() / 1e-5)
        assert np.count_nonzero(mask) > 100
        expected = m.thickness * m.static_field(p[mask])
        assert np.max(np.abs(v_fe[mask] - expected)) < 5.0e-2

    def test_hysteresis_loop_closes(self):
        # A full 0 -> +V -> -V -> 0 period switches the state once net, so
        # every period ends at -Ps regardless of the starting branch; the
        # second period confirms the stable limit cycle.
        m = LKCircuitModel(**{**FE_MODEL.__dict__, "rs": 0.0})
        v_max = 2.5 * m.ec_static() * m.thickness
        first = run_triangular_sweep(m, v_max=v_max, period=1.0e-3, n_steps=20000)
        second = run_triangular_sweep(
            m, v_max=v_max, period=1.0e-3, n_steps=20000, p0=first["P"][-1],
        )
        assert abs(first["P"][-1] + m.ps()) < 0.05 * m.ps()
        assert abs(second["P"][-1] + m.ps()) < 0.05 * m.ps()


class TestEnergyLedger:
    def test_energy_identity_closes(self):
        sweep = run_triangular_sweep(
            FE_MODEL,
            v_max=2.5 * FE_MODEL.ec_static() * FE_MODEL.thickness,
            period=1.0e-6,
            n_steps=20000,
        )
        scale = max(abs(sweep["E_source"]), 1e-30)
        # The switching transient dominates the residual (trapezoid on a
        # stiff traverse); the identity closes at the percent level.
        assert abs(sweep["energy_residual"]) / scale < 3e-2

    def test_ideal_drive_has_no_joule_heat(self):
        m = LKCircuitModel(**{**FE_MODEL.__dict__, "rs": 0.0})
        sweep = run_triangular_sweep(m, v_max=0.5, period=1.0e-6, n_steps=4000)
        assert sweep["E_joule"] == 0.0


class TestDualVerdict:
    @staticmethod
    def _pulse_case(rs):
        model = LKCircuitModel(
            alpha=-5.0e8, beta=1.5e9, gamma=1.0e3,
            epsilon_r=20.0, thickness=10.0e-9, area=1.0e-12, rs=rs,
        )
        v_step = 2.5 * model.ec_static() * model.thickness
        return nc_verdict(model, v_step=v_step, hold_time=1.0e-5, n_steps=20000)

    def test_ideal_drive_never_dips(self):
        # By construction V_fe == V_a under Rs = 0: any terminal dip in a
        # real measurement is the source-impedance drop (Alexe mechanism).
        result = self._pulse_case(1.0e6)
        assert result["dip_terminal_ideal_V"] == 0.0
        assert result["dip_terminal_measurement_V"] > 0.1

    def test_terminal_dip_grows_with_source_impedance(self):
        dips = [self._pulse_case(rs)["dip_terminal_measurement_V"]
                for rs in (50.0, 1.0e3, 1.0e5, 1.0e6)]
        assert all(b > a for a, b in zip(dips, dips[1:]))

    def test_branch_dip_equals_s_curve_span(self):
        result = self._pulse_case(1.0e6)
        model = LKCircuitModel(
            alpha=-5.0e8, beta=1.5e9, gamma=1.0e3,
            epsilon_r=20.0, thickness=10.0e-9, area=1.0e-12, rs=1.0e6,
        )
        expected = 2.0 * model.ec_static() * model.thickness
        assert result["dip_branch_intrinsic_V"] == pytest.approx(expected, rel=0.15)

    def test_low_impedance_source_gives_intrinsic_only(self):
        # A 50-Ohm source on a micron-scale device manufactures only a
        # microvolt-level sag: the honest verdict is that the intrinsic
        # S-branch traverse dominates.
        result = self._pulse_case(50.0)
        assert result["dip_terminal_measurement_V"] < 1.0e-3
        assert result["verdict"] == "intrinsic_only"

    def test_measurement_source_impedance_gives_artifact(self):
        result = self._pulse_case(1.0e6)
        assert result["verdict"] == "artifact"
        assert result["dip_terminal_measurement_V"] > 0.1

    def test_linear_capacitor_gives_no_dip_verdict(self):
        m = LKCircuitModel(alpha=0.0, beta=0.0, gamma=1.0e12, rs=50.0)
        result = nc_verdict(m, v_step=1.0, hold_time=1.0e-6, n_steps=6000)
        assert result["verdict"] == "no_dip"
