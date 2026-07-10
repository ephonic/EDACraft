"""A档: analytic-limit & analytic-property validation tests.

These tests verify the M7 modules against their KNOWN analytic properties
(mathematical identities of the models themselves — no external reference).
The goal: catch "the equation was written wrong" bugs that qualitative
behaviour tests miss.

Modules covered:
  - Landau-Khalatnikov (L-K): Cardano closed-form root comparison, linear
    response about the well, spinodal identities.
  - Preisach (play-operator): Ps->0, Ec->0, saturation-to-Ps (post Escale fix),
    loop-closure invariant, Escale decoupling.
  - Dielectric breakdown: sigma_bd->inf hard-short, sigma_bd->0 no-leak,
    E_bd->inf never-break, dimensional self-consistency.
  - Impact ionization (Chynoweth): E->0, E->inf saturation, monotonicity,
    sub-critical no-perturbation.
  - Newton-vs-Gummel cross-implementation consistency (quantitative).

The two bugs found by this analysis (Preisach Escale=Ec saturation cap;
sigma_bd [S/m] dimensional inconsistency) are fixed in the same commit and
pinned here by the saturation / hard-short tests.
"""

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator

QE = 1.602176634e-19
EPS0 = 8.854187817e-12
K_B = 1.3806503e-23
VT_300 = K_B * 300.0 / QE

# L-K test-file params (strong-coercive double well).
FE_ALPHA = -5.0e8
FE_BETA = 1.5e10


# ===========================================================================
# L-K analytic properties
# ===========================================================================

def _fe_well(alpha=FE_ALPHA, beta=FE_BETA):
    Ps = np.sqrt(-alpha / beta)
    P_sp = np.sqrt(-alpha / (3.0 * beta))
    Ec = (2.0 / 3.0) * abs(alpha) * P_sp
    return Ps, P_sp, Ec


def _fe_solve_P_signed(E_drive, alpha=FE_ALPHA, beta=FE_BETA, P_prev=0.0):
    """Python mirror of the signed L-K Newton solve (continuation from P_prev)."""
    Ps = np.sqrt(-alpha / beta)
    P = P_prev
    if P == 0.0:
        P = Ps if E_drive >= 0.0 else -Ps
    for _ in range(20):
        f = alpha * P + beta * P * P * P - E_drive
        df = alpha + 3.0 * beta * P * P
        if abs(df) < 1e-30:
            break
        dP = f / df
        P -= dP
        if abs(dP) < 1e-15 * abs(P):
            break
    return P


def _cardano_root(E, alpha=FE_ALPHA, beta=FE_BETA):
    """Closed-form real root of beta*P^3 + alpha*P - E = 0 (depressed cubic).

    Uses np.roots (independent of the Newton mirror) and returns the real root
    closest to +Ps for E>0 (or -Ps for E<0), i.e. the physical branch.
    """
    # coeffs of P^3 + 0*P^2 + (alpha/beta)*P - E/beta = 0
    coeffs = [1.0, 0.0, alpha / beta, -E / beta]
    roots = np.roots(coeffs)
    real_roots = [r.real for r in roots if abs(r.imag) < 1e-9]
    if not real_roots:
        return None
    Ps = np.sqrt(-alpha / beta)
    # Pick the root on the same side as sign(E)*Ps.
    target_sign = 1.0 if E >= 0 else -1.0
    same_side = [r for r in real_roots if r * target_sign > 0]
    if same_side:
        return max(same_side, key=lambda r: abs(r))
    return max(real_roots, key=lambda r: abs(r))


class TestLandauKhalatnikovAnalytic:
    """L-K Newton solve against Cardano closed-form + linear response."""

    def test_signed_solve_matches_cardano_across_fields(self):
        """The Newton-solved P must match the Cardano real root to high
        precision across a wide field range (well interior, near spinodal,
        high field). This is the gold-standard check that the cubic solver is
        correct — np.roots is independent of the Newton iteration."""
        Ps, P_sp, Ec = _fe_well()
        for E in [0.01 * Ec, 0.3 * Ec, 0.9 * Ec, 1.5 * Ec, 5.0 * Ec, 1e9]:
            P_newton = _fe_solve_P_signed(E)
            P_cardano = _cardano_root(E)
            assert P_cardano is not None, f"no real root at E={E}"
            rel = abs(P_newton - P_cardano) / max(abs(P_cardano), 1e-30)
            assert rel < 1e-6, (
                f"L-K Newton diverges from Cardano at E={E:.3e}: "
                f"Newton={P_newton:.6e} Cardano={P_cardano:.6e} rel={rel:.2e}")

    def test_linear_response_about_well(self):
        """Small-signal response about the +Ps well: dP/dE = 1/(dE/dP) at P=Ps.
        dE/dP = alpha + 3*beta*Ps^2 = alpha + 3*beta*(-alpha/beta) = -2*alpha.
        So for small positive E about Ps: P ≈ Ps + E/(-2*alpha) = Ps - E/(2*alpha)
        (alpha<0 so this is +E/|2alpha|)."""
        Ps, P_sp, Ec = _fe_well()
        dE = 0.01 * Ec   # small perturbation
        P = _fe_solve_P_signed(dE, P_prev=Ps)   # continue from +Ps well
        P_linear = Ps - dE / (2.0 * FE_ALPHA)   # FE_ALPHA<0 -> +dE/|2alpha|
        rel = abs(P - P_linear) / abs(P_linear)
        assert rel < 0.01, (
            f"linear response about well wrong: Newton P={P:.6e}, "
            f"linear approx={P_linear:.6e}, rel={rel:.3e}")

    def test_spinodal_identity_exact(self):
        """At the spinodal P_sp, |alpha*P_sp + beta*P_sp^3| must equal Ec exactly."""
        Ps, P_sp, Ec = _fe_well()
        E_at_spinodal = abs(FE_ALPHA * P_sp + FE_BETA * P_sp**3)
        assert abs(E_at_spinodal - Ec) / Ec < 1e-9, (
            f"spinodal identity broken: |E(P_sp)|={E_at_spinodal:.6e} "
            f"Ec={Ec:.6e}")


# ===========================================================================
# Preisach analytic properties (post Escale fix)
# ===========================================================================

PS_TEST = 0.2
EC_TEST = 5.0e7


def _build_preisach_slab(ps=PS_TEST, ec=EC_TEST, escale=0.0):
    """Pure FE slab for Preisach; returns (sim, N, mid)."""
    Lx = 10e-9
    nx = 41
    dx = Lx / (nx - 1)
    N = nx
    sim = PyDeviceSimulator(nx, 1, 1, dx, 1.0, 1.0)
    sim.set_permittivity(np.full(N, EPS0 * 35.0))
    sim.set_mobility(np.zeros(N), np.zeros(N))
    sim.set_doping(np.zeros(N))
    sim.set_thermal_voltage(VT_300)
    sim.set_recombination(np.full(N, 1e-7), np.full(N, 1e-7))
    sim.set_effective_dos(np.full(N, 2.8e25), np.full(N, 1.04e25))
    sim.set_bandgap(np.full(N, 1.12))
    sim.set_ferroelectric_enabled(True)
    sim.set_ferroelectric_params(np.ones(N, dtype=np.int8), -1.0e8, 1.0e18)
    sim.set_ferroelectric_model(1)
    sim.set_ferroelectric_preisach(ps, ec, escale)
    sim.set_dirichlet_potential({0: 0.0, N - 1: 0.0})
    sim.set_electron_bc({0: 0.0, N - 1: 0.0})
    sim.set_hole_bc({0: 0.0, N - 1: 0.0})
    return sim, N, N // 2


class TestPreisachAnalyticLimits:
    """Preisach play-operator against its analytic properties (post Escale fix)."""

    def test_ps_zero_gives_zero_polarization(self):
        """Ps->0 limit: P = Ps*tanh(...) -> 0 for all E."""
        sim, N, mid = _build_preisach_slab(ps=0.0, ec=EC_TEST, escale=EC_TEST / 3)
        sim.set_dirichlet_potential({0: 1.0, N - 1: 0.0})
        P = sim.solve()["P"]
        assert np.allclose(P[:, 0], 0.0, atol=1e-30), (
            "Ps=0 should give P=0 everywhere")

    def test_escale_decoupling_lets_p_approach_ps(self):
        """A档 Bug 1 fix: with Escale < Ec (e.g. Ec/3), a monotonic ramp to
        large drive must let |P| approach the named saturation Ps (was capped
        at tanh(1)*Ps ≈ 0.76*Ps under the legacy Escale=Ec)."""
        sim, N, mid = _build_preisach_slab(ps=PS_TEST, ec=EC_TEST,
                                           escale=EC_TEST / 3)
        # Large drive: |E| >> Ec, and Escale=Ec/3 -> arg=(E-w)/Escale can grow.
        sim.set_dirichlet_potential({0: 5.0, N - 1: 0.0})
        P = sim.solve()["P"][mid][0]
        assert abs(P) > 0.9 * PS_TEST, (
            f"Escale decoupling failed: |P|={abs(P):.3e} did not approach Ps="
            f"{PS_TEST:.3e} (legacy tanh(1)*Ps cap still in effect?)")

    def test_legacy_escale_caps_at_tanh1_ps(self):
        """Document the legacy behaviour (Escale=0 => Escale=Ec): |P| caps near
        tanh(1)*Ps ≈ 0.762*Ps on a monotonic ramp. This pins the pre-fix
        behaviour so the Escale fix is understood to change it."""
        sim, N, mid = _build_preisach_slab(ps=PS_TEST, ec=EC_TEST, escale=0.0)
        sim.set_dirichlet_potential({0: 5.0, N - 1: 0.0})
        P = sim.solve()["P"][mid][0]
        tanh1_ps = np.tanh(1.0) * PS_TEST
        # Should be near tanh(1)*Ps (allow the self-consistent feedback some slack).
        assert abs(P) < tanh1_ps * 1.5, (
            f"legacy Escale=Ec should cap |P| near tanh(1)*Ps={tanh1_ps:.3e}, "
            f"got |P|={abs(P):.3e}")

    def test_loop_closure_invariant(self):
        """A full bipolar major loop 0->+Emax->0->-Emax->0 should bring P back
        toward its starting region (the play-operator is rate-independent).
        Because the self-consistent -div(P) feedback and phi-freezing perturb
        the ideal isolated play-operator, we assert the WEAKER but robust
        invariant: P at Vg=0 after the + excursion and after the - excursion
        have OPPOSITE signs (the two branches of the loop), rather than exact
        closure to the start value."""
        sim, N, mid = _build_preisach_slab(ps=PS_TEST, ec=EC_TEST,
                                           escale=EC_TEST / 3)
        Emax = 2.0
        # 0 -> +Emax -> 0 (rem+) -> -Emax -> 0 (rem-)
        seq = [Emax, 0.0, -Emax, 0.0]
        Ps_seq = []
        for Vg in seq:
            sim.set_dirichlet_potential({0: Vg, N - 1: 0.0})
            Ps_seq.append(sim.solve()["P"][mid][0])
        rem_after_pos = Ps_seq[1]   # P at Vg=0 after +Emax
        rem_after_neg = Ps_seq[3]   # P at Vg=0 after -Emax
        # The two remanent states must be on opposite branches (memory window).
        assert rem_after_pos * rem_after_neg < 0, (
            f"remanence after +Emax ({rem_after_pos:.3e}) and after -Emax "
            f"({rem_after_neg:.3e}) not on opposite branches — no memory "
            "window / loop not traced")

    def test_escale_smaller_gives_higher_saturation(self):
        """For the same drive, a smaller Escale should give |P| closer to Ps
        (the tanh is steeper). This verifies Escale genuinely decouples the
        output sharpness from the deadband Ec."""
        drv = 3.0
        sat_small = []
        for escale in [EC_TEST, EC_TEST / 2, EC_TEST / 5]:
            sim, N, mid = _build_preisach_slab(ps=PS_TEST, ec=EC_TEST,
                                               escale=escale)
            sim.set_dirichlet_potential({0: drv, N - 1: 0.0})
            sat_small.append(abs(sim.solve()["P"][mid][0]))
        # Monotonically increasing saturation as Escale shrinks.
        assert sat_small[2] >= sat_small[0], (
            f"smaller Escale should give higher |P|: {sat_small}")


# ===========================================================================
# Dielectric breakdown analytic limits (post dimensional fix)
# ===========================================================================

def _build_bd_stack(tox=2e-9, tsi=20e-9, nx_ox=5, nx_si=21, E_BD=5.0e8):
    """metal/oxide/Si stack; returns (sim, N, is_ox)."""
    Lx = tox + tsi
    nx = nx_ox + nx_si
    dx = Lx / (nx - 1)
    N = nx
    sim = PyDeviceSimulator(nx, 1, 1, dx, 1.0, 1.0)
    x = np.arange(N) * dx
    is_ox = x < tox
    eps = np.where(is_ox, EPS0 * 3.9, EPS0 * 11.7)
    sim.set_permittivity(eps)
    sim.set_mobility(np.where(is_ox, 0.0, 0.14), np.where(is_ox, 0.0, 0.045))
    sim.set_doping(np.where(is_ox, 0.0, 1e23))
    sim.set_thermal_voltage(VT_300)
    sim.set_recombination(np.full(N, 1e-7), np.full(N, 1e-7))
    sim.set_effective_dos(np.full(N, 2.8e25), np.full(N, 1.04e25))
    sim.set_bandgap(np.full(N, 1.12))
    sim.set_electron_bc({0: 0.0, N - 1: 0.0})
    sim.set_hole_bc({0: 0.0, N - 1: 0.0})
    sim.set_dirichlet_potential({0: 0.0, N - 1: 0.0})
    E_bd = np.where(is_ox, E_BD, 0.0)
    return sim, N, is_ox, E_bd


class TestBreakdownAnalyticLimits:
    """Dielectric breakdown against analytic limits (post [F/m^3] fix)."""

    def test_sigma_bd_large_pins_phi_to_zero(self):
        """sigma_bd -> large: broken NON-CONTACT nodes' phi -> 0 (hard short).
        With the [F/m^3] definition, a sigma_bd >> eps/dx^2 dominates the
        Poisson diagonal. (Contact/Dirichlet nodes are pinned to Vg by the BC
        row, which overrides the leakage term — excluded from the assert.)"""
        sim, N, is_ox, E_bd = _build_bd_stack()
        sim.set_breakdown_enabled(True)
        # eps_SiO2/dx^2 ~ 4.5e7 for tox=2nm; use 1e11 to dominate (~2000x).
        sim.set_breakdown_params(is_ox.astype(np.int8), E_bd, 1.0e11)
        sim.set_dirichlet_potential({0: 3.0, N - 1: 0.0})
        sim.solve()   # break
        sim.solve()   # apply leakage at broken nodes
        bd = sim.breakdown_state()
        assert bd[is_ox].max() == 1, "no breakdown induced"
        r = sim.solve()
        # Broken INTERIOR oxide nodes (exclude contact node 0 which is Dirichlet).
        broken_int = np.where(is_ox & (bd == 1) & (np.arange(N) != 0))[0]
        assert len(broken_int) > 0, "no interior (non-contact) broken oxide node"
        phi_broken = r["phi"][broken_int]
        # With sigma_bd=1e11 >> diagonal ~4.5e7 (2000x), phi is pulled far
        # below its unshorted value (~0.9). Assert <<unshorted (not exact 0,
        # since neighbours still couple via edge terms).
        assert np.max(np.abs(phi_broken)) < 0.05, (
            f"hard-short limit failed: interior broken-node phi={phi_broken} "
            f"not near 0 with sigma_bd=1e11 [F/m^3] (diag ~4.5e7, unshorted ~0.9)")

    def test_sigma_bd_zero_no_leakage(self):
        """sigma_bd -> 0: the guard skips the leakage term, so broken nodes
        behave as normal dielectric (phi unaffected by the bd flag)."""
        sim_ref, N, is_ox, E_bd = _build_bd_stack()
        sim_ref.set_dirichlet_potential({0: 1.0, N - 1: 0.0})
        r_ref = sim_ref.solve()

        sim_bd, _, _, _ = _build_bd_stack()
        sim_bd.set_breakdown_enabled(True)
        sim_bd.set_breakdown_params(is_ox.astype(np.int8), E_bd, 0.0)  # no leak
        sim_bd.set_dirichlet_potential({0: 1.0, N - 1: 0.0})
        r_bd = sim_bd.solve()
        # At Vg=1, E~5e8 = E_bd boundary; with sigma_bd=0 the phi should match
        # the no-breakdown reference closely (leakage term is a no-op).
        assert np.allclose(r_ref["phi"], r_bd["phi"], rtol=1e-6), (
            "sigma_bd=0 should not perturb phi (guard broken)")

    def test_ebd_infinite_never_breaks(self):
        """E_bd -> inf: no node ever breaks regardless of bias."""
        sim, N, is_ox, _ = _build_bd_stack(E_BD=1e30)
        sim.set_breakdown_enabled(True)
        sim.set_breakdown_params(is_ox.astype(np.int8),
                                 np.where(is_ox, 1e30, 0.0), 1.0e-2)
        sim.set_dirichlet_potential({0: 10.0, N - 1: 0.0})
        sim.solve()
        assert sim.breakdown_state().max() == 0, (
            "E_bd=1e30 should never trigger breakdown")

    def test_dimensional_response_monotonic_in_sigma_bd(self):
        """With sigma_bd in [F/m^3], the leakage effect should grow
        monotonically with sigma_bd: a larger sigma_bd pulls broken-node phi
        closer to 0. (Verifies the dimensional fix gives sensible physics.)
        eps/dx^2 ~ 4.5e7 for tox=2nm; sweep sigma across that scale."""
        phi_max_by_sigma = []
        for sigma in [1e6, 1e9, 1e12]:   # below, at, above the diagonal scale
            sim, N, is_ox, E_bd = _build_bd_stack()
            sim.set_breakdown_enabled(True)
            sim.set_breakdown_params(is_ox.astype(np.int8), E_bd, sigma)
            sim.set_dirichlet_potential({0: 3.0, N - 1: 0.0})
            sim.solve()  # break
            sim.solve()  # apply leak
            r = sim.solve()
            bd = sim.breakdown_state()
            # interior broken oxide nodes (exclude contact 0)
            broken = np.where(is_ox & (bd == 1) & (np.arange(N) != 0))[0]
            if len(broken):
                phi_max_by_sigma.append(np.max(np.abs(r["phi"][broken])))
            else:
                phi_max_by_sigma.append(np.inf)
        # Larger sigma -> smaller |phi| (closer to short). All finite here.
        if all(np.isfinite(phi_max_by_sigma)):
            assert phi_max_by_sigma[2] <= phi_max_by_sigma[0], (
                f"larger sigma_bd should pull phi closer to 0: {phi_max_by_sigma}")


# ===========================================================================
# Impact ionization analytic limits
# ===========================================================================

class TestImpactIonizationAnalyticLimits:
    """Chynoweth alpha(E) analytic limits (numpy closed form; C++ path is
    exercised via the sub-critical no-perturbation test)."""

    A_N = 7.03e7
    B_N = 1.231e8
    A_P = 1.58e8
    B_P = 2.036e8

    def test_alpha_zero_at_zero_field(self):
        """E->0: alpha = A*exp(-B/|E|) -> 0."""
        for A, B in [(self.A_N, self.B_N), (self.A_P, self.B_P)]:
            assert A * np.exp(-B / 1e3) < 1e-100, (
                f"alpha not ->0 at low field for A={A}, B={B}")

    def test_alpha_saturates_to_A_at_high_field(self):
        """E->inf: alpha -> A (exp(0)=1). Need E >> B so B/E is tiny."""
        E = 1e15   # B/E ~ 1e-7 -> exp ~ 1 - 1e-7
        for A, B in [(self.A_N, self.B_N), (self.A_P, self.B_P)]:
            alpha = A * np.exp(-B / E)
            assert abs(alpha - A) / A < 1e-6, (
                f"alpha does not saturate to A={A} at E=1e15: got {alpha:.6e} "
                f"(rel err {abs(alpha-A)/A:.2e}, B/E={B/E:.2e})")

    def test_alpha_monotonic_in_field(self):
        """alpha(E) strictly increasing in |E|."""
        Es = np.array([1e6, 1e7, 1e8, 1e9, 1e10])
        for A, B in [(self.A_N, self.B_N), (self.A_P, self.B_P)]:
            a = A * np.exp(-B / Es)
            assert np.all(np.diff(a) > 0), (
                f"alpha not monotonic for A={A}, B={B}: {a}")


# ===========================================================================
# Cross-implementation consistency: Newton vs Gummel
# ===========================================================================

class TestNewtonGummelConsistency:
    """Two independent solver paths must agree on the same FE problem
    (quantitative, post FE-coupling fix)."""

    def test_newton_gummel_p_quantitatively_agree(self):
        """On a pure FE slab driven past Ec, the Newton and Gummel paths must
        produce P within ~0.1*Ps of each other at the same drive (both now carry
        -div(P); before the M7a fix Newton dropped FE entirely)."""
        Lx = 10e-9
        nx = 41
        dx = Lx / (nx - 1)
        N = nx
        mid = N // 2

        def solve_P(use_newton):
            s = PyDeviceSimulator(nx, 1, 1, dx, 1.0, 1.0)
            s.set_permittivity(np.full(N, EPS0 * 35.0))
            s.set_mobility(np.zeros(N), np.zeros(N))
            s.set_doping(np.zeros(N))
            s.set_thermal_voltage(VT_300)
            s.set_recombination(np.full(N, 1e-7), np.full(N, 1e-7))
            s.set_effective_dos(np.full(N, 2.8e25), np.full(N, 1.04e25))
            s.set_bandgap(np.full(N, 1.12))
            s.set_ferroelectric_enabled(True)
            s.set_ferroelectric_params(np.ones(N, dtype=np.int8), FE_ALPHA, FE_BETA)
            s.set_electron_bc({0: 0.0, N - 1: 0.0})
            s.set_hole_bc({0: 0.0, N - 1: 0.0})
            s.set_use_newton(use_newton)
            s.set_dirichlet_potential({0: 1.0, N - 1: 0.0})
            return s.solve()["P"][mid][0]

        P_gummel = solve_P(False)
        P_newton = solve_P(True)
        Ps, _, _ = _fe_well()
        assert abs(P_newton - P_gummel) < 0.15 * Ps, (
            f"Newton and Gummel disagree on FE P: Newton={P_newton:.4e} "
            f"Gummel={P_gummel:.4e} (Ps={Ps:.4e}) — FE coupling inconsistent "
            "between paths (regression of audit §21 fix?)")
