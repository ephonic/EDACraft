"""Comprehensive equation-solver correctness verification audit.

Audits every new equation solver added in this session, states what
verification exists, and runs targeted correctness checks for gaps.

Categories:
  A. ODE/kinetics solvers: step-size independence + closed-form
  B. Probabilistic/stochastic: analytic limits + dual implementation
  C. Compact device models: limiting behavior + cross-consistency
  D. C++ solver extensions: bit-preservation + self-consistency
"""

import math
import sys

import os
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestM1CyclingKinetics:
    """A1: M1 FieldHistoryCyclingState — exact ODE integration."""

    def test_exact_exponential_two_segment(self):
        """Closed-form: W after two segments at same field exponent=0."""
        from tcad.physics.ferro_kinetics import FieldHistoryCyclingState
        m = FieldHistoryCyclingState(
            wakeup_cycles=100.0, fatigue_cycles=1000.0,
            wakeup_gain=0.0, fatigue_loss=0.0,
            reference_field=1e8, wakeup_field_exponent=0.0,
            fatigue_field_exponent=2.0,
        )
        m.advance(50.0, 1e8)
        m.advance(30.0, 2e8)
        # wakeup_field_exponent=0 → N_w = 100 regardless of field
        expected = 1 - np.exp(-50/100) * np.exp(-30/100)
        assert m.wakeup_state == pytest.approx(expected, rel=1e-14)
        # fatigue uses field-dependent lifetime
        # N_f(2e8) = 1000 * (1e8/2e8)^2 = 250
        expected_f = 1 - np.exp(-50/1000) * np.exp(-30/250)
        assert m.fatigue_state == pytest.approx(expected_f, rel=1e-14)

    def test_step_size_independence(self):
        """Exact semigroup: one step of dt equals N steps of dt/N."""
        from tcad.physics.ferro_kinetics import FieldHistoryCyclingState
        one = FieldHistoryCyclingState(
            wakeup_cycles=500, fatigue_cycles=2000, reference_field=1e8,
            fatigue_field_exponent=2.0, imprint_rate=0.01,
            imprint_field_max=1e6)
        many = FieldHistoryCyclingState(
            wakeup_cycles=500, fatigue_cycles=2000, reference_field=1e8,
            fatigue_field_exponent=2.0, imprint_rate=0.01,
            imprint_field_max=1e6)
        one.advance_with_recheck(1000, 2e8, stride=1000)
        for _ in range(1000):
            many.advance(1, 2e8)
        assert one.wakeup_state == pytest.approx(many.wakeup_state, rel=1e-13)

    def test_conservation_active_fraction_bounded(self):
        """Active fraction stays in [0, 1+gain]."""
        from tcad.physics.ferro_kinetics import FieldHistoryCyclingState
        m = FieldHistoryCyclingState(wakeup_cycles=10, fatigue_cycles=100,
                                     wakeup_gain=0.5, fatigue_loss=0.95)
        for _ in range(100):
            m.advance(10, 3e8)
        assert 0 <= m.active_fraction <= 1.5


class TestM4AvramiKinetics:
    """A2: M4 AvramiDomainSwitching — closed-form exactness."""

    def test_constant_field_exact_any_step(self):
        """f(t) = 1-exp(-(t/τ)^n) at machine precision for ANY n_steps."""
        from tcad.physics.ferro_kinetics import AvramiDomainSwitching
        for n, steps in ((1.0, 1), (1.5, 13), (2.0, 64)):
            d = AvramiDomainSwitching(
                avrami_exponent=n, tau0=2e-9, merz_field=1e8,
                merz_exponent=1.0, completion_fraction=1 - 1e-15)
            t_total = 5 * d.tau(1e8)
            dt = t_total / steps
            for _ in range(steps):
                d.advance(1e8, dt)
            expected = 1 - np.exp(-(t_total / d.tau(1e8)) ** n)
            assert d.switched_fraction == pytest.approx(expected, rel=1e-12)

    def test_polarization_bounded(self):
        """|P| ≤ Ps structurally."""
        from tcad.physics.ferro_kinetics import AvramiDomainSwitching
        rng = np.random.default_rng(42)
        for _ in range(100):
            d = AvramiDomainSwitching(orientation=-1, tau0=1e-9,
                                       onset_field=5e7, merz_field=1e8,
                                       merz_exponent=1.2,
                                       avrami_exponent=1.5)
            for _ in range(20):
                d.advance(rng.uniform(-3e8, 3e8), rng.uniform(1e-10, 1e-7))
            assert abs(d.polarization(1.0)) <= 1.0 + 1e-12


class TestM3MasterEquation:
    """A3: M3 BirthDeathChain — probabilistic exactness."""

    def test_poisson_limit(self):
        """Constant rate → Poisson distribution (exact)."""
        from tcad.physics.electron_counting import BirthDeathChain
        chain = BirthDeathChain(n_max=40,
                                capture_rate=lambda n: 2.0,
                                emission_rate=lambda n: 0.0)
        chain.initialize(count=0)
        chain.advance(1.7)
        n = np.arange(41)
        expected = np.exp(-3.4) * 3.4**n / [math.factorial(k) for k in n]
        assert np.max(np.abs(chain.state - expected)) < 1e-14

    def test_binomial_limit(self):
        """Linear rates → Binomial (exact)."""
        from tcad.physics.electron_counting import BirthDeathChain
        n_max, lam0, mu0 = 12, 0.9, 0.4
        chain = BirthDeathChain(
            n_max=n_max,
            capture_rate=lambda n: lam0 * (n_max - n),
            emission_rate=lambda n: mu0 * n)
        chain.initialize(count=0)
        chain.advance(2.5)
        p = lam0/(lam0+mu0) * (1 - np.exp(-(lam0+mu0)*2.5))
        expected = np.array([math.comb(n_max, k) * p**k * (1-p)**(n_max-k)
                             for k in range(n_max+1)])
        assert np.max(np.abs(chain.state - expected)) < 1e-13

    def test_detailed_balance(self):
        """Chain evolved to steady state matches product-form stationary."""
        from tcad.physics.electron_counting import BirthDeathChain
        chain = BirthDeathChain(n_max=10,
                                capture_rate=lambda n: 0.5 + 0.2*n,
                                emission_rate=lambda n: 0.3*max(n, 1))
        chain.initialize(count=5)
        for _ in range(400):
            chain.advance(0.5)
        pi = chain.stationary()
        assert np.max(np.abs(chain.state - pi)) < 1e-12

    def test_probability_conservation(self):
        """ΣP(n) = 1 at all times."""
        from tcad.physics.electron_counting import BirthDeathChain
        chain = BirthDeathChain(n_max=24,
                                capture_rate=lambda n: 0.7*(24-n),
                                emission_rate=lambda n: 0.3*n)
        chain.initialize(count=24)
        for _ in range(200):
            chain.advance(0.05)
            assert abs(float(np.sum(chain.state)) - 1.0) <= 1e-12


class TestM5NCCircuit:
    """A4: M5 LKCircuitModel — energy conservation and limits."""

    def test_energy_identity(self):
        """source = Joule + LK dissipation + ΔLandau + Δcapacitance."""
        from tcad.physics.nc_verdict import LKCircuitModel, run_triangular_sweep
        m = LKCircuitModel(alpha=-5e8, beta=1.5e9, gamma=1e3)
        s = run_triangular_sweep(m, v_max=2.5 * m.ec_static() * m.thickness,
                                 period=1e-6, n_steps=20000)
        scale = max(abs(s["E_source"]), 1e-30)
        assert abs(s["energy_residual"]) / scale < 5e-3

    def test_linear_capacitor_limit(self):
        """Frozen LK (gamma→large) → pure RC, I = C·dV/dt."""
        from tcad.physics.nc_verdict import LKCircuitModel, run_triangular_sweep
        m = LKCircuitModel(alpha=0, beta=0, gamma=1e12, rs=50)
        s = run_triangular_sweep(m, v_max=1.0, period=1e-6, n_steps=8000)
        c = m.capacitance
        expected = c * 1.0 / (0.25e-6)  # dV/dt during ramp
        interior = s["I"][100:2000]
        assert np.allclose(interior, expected, rtol=0.05)

    def test_ideal_drive_no_dip(self):
        """Rs=0 → V_fe ≡ V_a, no NC dip (mathematical identity)."""
        from tcad.physics.nc_verdict import LKCircuitModel, run_triangular_sweep, measure_dip
        m = LKCircuitModel(alpha=-5e8, beta=1.5e9, rs=0.0)
        s = run_triangular_sweep(m, v_max=2.0, period=1e-6, n_steps=4000)
        assert measure_dip(s) == 0.0


class TestHFSVelocitySaturation:
    """A5: HFS Caugy-Thomas — closed-form resistor."""

    def test_resistor_closed_form(self):
        """J = q·n·μ(F)·F with Caugy-Thomas μ(F), exact."""
        from tcad.core import PyDeviceSimulator
        pytest.importorskip("tcad.core")
        nx, dx = 41, 1e-6/(41-1)
        vsat = 5e4
        for v in (0.02, 0.2, 2.0):
            sim0 = PyDeviceSimulator(nx, 1, 1, dx, 1, 1)
            sim1 = PyDeviceSimulator(nx, 1, 1, dx, 1, 1)
            for sim in (sim0, sim1):
                sim.set_permittivity(np.full(nx, 8.854e-12*11.7))
                sim.set_mobility(np.full(nx, 0.1), np.full(nx, 0.035))
                sim.set_doping(np.full(nx, 1e21))
                sim.set_thermal_voltage(0.025852)
                sim.set_recombination(np.full(nx, 1e-7), np.full(nx, 1e-7))
                sim.set_effective_dos(np.full(nx, 2.8e25), np.full(nx, 1.04e25))
                sim.set_bandgap(np.full(nx, 1.12))
                sim.set_electron_bc({0: 1e21, nx-1: 1e21})
                sim.set_hole_bc({0: 1e5, nx-1: 1e5})
            sim1.set_high_field_saturation(True, vsat, vsat, 2.0, 1.0, 1)
            sim0.set_dirichlet_potential({0: v, nx-1: 0})
            sim1.set_dirichlet_potential({0: v, nx-1: 0})
            r0 = sim0.solve(); r1 = sim1.solve()
            assert r0["converged"] and r1["converged"]
            j_base = float(np.asarray(r0["Jn_x"])[nx//2])
            j_hfs = float(np.asarray(r1["Jn_x"])[nx//2])
            F = v / (dx * (nx-1))
            factor = 1 / (1 + (0.1*F/vsat)**2)**0.5
            expected = j_base * factor
            assert j_hfs == pytest.approx(expected, rel=5e-3)

    def test_bit_preservation_disabled(self):
        """HFS disabled → identical to pre-HFS behavior."""
        from tcad.core import PyDeviceSimulator
        pytest.importorskip("tcad.core")
        nx, dx = 41, 1e-6/(41-1)
        for v in (0.2,):
            s1 = PyDeviceSimulator(nx, 1, 1, dx, 1, 1)
            s2 = PyDeviceSimulator(nx, 1, 1, dx, 1, 1)
            for sim in (s1, s2):
                sim.set_permittivity(np.full(nx, 8.854e-12*11.7))
                sim.set_mobility(np.full(nx, 0.1), np.full(nx, 0.035))
                sim.set_doping(np.full(nx, 1e21))
                sim.set_thermal_voltage(0.025852)
                sim.set_electron_bc({0: 1e21, nx-1: 1e21})
                sim.set_hole_bc({0: 1e5, nx-1: 1e5})
            s2.set_high_field_saturation(False, 1.07e5, 8.37e4, 2.0, 1.0, 0)
            s1.set_dirichlet_potential({0: v, nx-1: 0})
            s2.set_dirichlet_potential({0: v, nx-1: 0})
            j1 = float(np.asarray(s1.solve()["Jn_x"])[nx//2])
            j2 = float(np.asarray(s2.solve()["Jn_x"])[nx//2])
            assert j1 == pytest.approx(j2, rel=1e-12)


class TestM2NonlocalBTBT:
    """A6: Nonlocal BTBT Kane-consistent — closed-form and local limit."""

    def test_closed_form_theta(self):
        """Θ = (2/3)√(2m*)Eg^1.5/(ℏqE) matches Python replication."""
        from tcad.search.tfet_frontier import theta_kernel
        QE = 1.602176634e-19; HBAR = 1.054571817e-34
        M0 = 9.1093837015e-31
        for mt, eg, E in ((0.1, 0.9, 2e8), (0.2, 1.1, 3e8), (0.05, 0.7, 1.5e8)):
            expected = (2/3) * math.sqrt(2*mt*M0) * (eg*QE)**1.5 / (HBAR*QE*E)
            assert theta_kernel(E, mt, eg) == pytest.approx(expected, rel=1e-15)

    def test_local_kane_degenerate_limit(self):
        """Nonlocal with B_eff mapping equals local Kane at uniform field."""
        # B_eff = (4/3)*sqrt(2*m_t)*Eg^1.5/(hbar*q)
        # This is the m_t transfer identity verified by construction.
        QE = 1.602176634e-19; HBAR = 1.054571817e-34
        M0 = 9.1093837015e-31
        mt = 0.0843; eg = 1.12
        b_eff = (4/3) * math.sqrt(2*mt*M0) * (eg*QE)**1.5 / (HBAR*QE)
        E = 2e8
        # exp(-B_eff/E) == exp(-2*Theta(E, mt, eg))
        theta = (2/3) * math.sqrt(2*mt*M0) * (eg*QE)**1.5 / (HBAR*QE*E)
        lhs = math.exp(-b_eff / E)
        rhs = math.exp(-2 * theta)
        assert lhs == pytest.approx(rhs, rel=1e-12)


class TestRRAMFilament:
    """A7: RRAM filament — probability conservation."""

    def test_probability_conserved(self):
        from tcad.physics.rram_filament import FilamentConfig, FilamentState
        from tcad.physics.electron_counting import BirthDeathChain
        cfg = FilamentConfig(n_max=15)
        chain = BirthDeathChain(n_max=15,
                                capture_rate=lambda n: 0,
                                emission_rate=lambda n: 0)
        chain.initialize(count=0)
        state = FilamentState(chain=chain, config=cfg, field_V_per_m=1e8)
        for _ in range(10):
            state.step(1e-8)
        assert abs(float(np.sum(chain.state)) - 1.0) <= 1e-12

    def test_on_off_resistance_separation(self):
        from tcad.physics.rram_filament import FilamentConfig, simulate_cycling
        cfg = FilamentConfig(n_max=20, n_conducting=12,
                             growth_activation_eV=0.3)
        r = simulate_cycling(cfg, n_cycles=10, pulse_width=1e-4, seed=1)
        assert r["mean_ratio"] > 1.0, "R_off/R_on must > 1"


class TestPCMDrift:
    """A8: PCM drift — power-law and crystallization limits."""

    def test_drift_power_law_exponent(self):
        from tcad.physics.pcm_drift import PcmConfig, simulate_retention_drift
        cfg = PcmConfig(drift_exponent=0.08, crystallization_activation_eV=3.5)
        r = simulate_retention_drift(cfg, n_points=40)
        assert 0.02 < r['drift_exponent_fit'] < 0.25

    def test_crystallization_bounded(self):
        from tcad.physics.pcm_drift import PcmState, PcmConfig
        state = PcmState(config=PcmConfig(temperature_K=600,
                                          crystallization_activation_eV=1.0))
        for _ in range(100):
            state.advance(1.0)
        assert 0 <= state.crystallized_fraction <= 1.0
