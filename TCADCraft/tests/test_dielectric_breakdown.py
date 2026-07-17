"""Tests for the M7b dielectric breakdown model (audit §22).

Goes straight to the C++ core via ``tcad.core.PyDeviceSimulator`` (like
``test_fe_coupling_and_ionization.py``) to isolate the solver numerics.

Three regression targets:
  1. The oxide electric field tracks Vg/tox (the field that drives breakdown).
  2. When |E| exceeds the material E_bd, the breakdown state flips (0 -> 1) at
     the over-stressed dielectric nodes.
  3. The breakdown is IRREVERSIBLE: lowering the bias afterwards does not clear
     the breakdown state (the conductive filament persists).
"""

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator

# Physical constants (SI), matched to the C++ core (math_types.h).
QE = 1.602176634e-19
EPS0 = 8.854187817e-12
K_B = 1.3806503e-23
VT_300 = K_B * 300.0 / QE          # ~0.025852 V


def _build_gate_oxide_stack(tox=2e-9, tsi=20e-9, nx_ox=5, nx_si=21):
    """1-D metal / oxide / silicon stack so the oxide field is well-resolved.

    Layout (x axis):
      [0, tox)               : gate oxide (SiO2, insulator, E_bd set)
      [tox, tox+tsi]         : silicon substrate (n-type)
    Contacts: x=0 (gate, driven) and x=last (substrate body, grounded).
    Returns (sim, N, oxide_node_ids, si_node_ids).
    """
    Lx = tox + tsi
    nx = nx_ox + nx_si
    dx = Lx / (nx - 1)
    N = nx
    sim = PyDeviceSimulator(nx, 1, 1, dx, 1.0, 1.0)

    # Per-node material assignment by position.
    x = np.arange(N) * dx
    is_ox = x < tox
    eps = np.where(is_ox, EPS0 * 3.9, EPS0 * 11.7)
    mu_n = np.where(is_ox, 0.0, 0.14)
    mu_p = np.where(is_ox, 0.0, 0.045)
    # n-type substrate doping (the oxide stays intrinsic / 0 net doping).
    doping = np.where(is_ox, 0.0, 1e23)
    # Breakdown field: set a LOW E_bd on the oxide so breakdown is reachable
    # at modest gate bias (the real SiO2 value 1.2e9 needs >2 V across 2 nm,
    # which is fine, but a lower threshold makes the test robust and fast).
    E_BD_TEST = 5.0e8   # V/m — deliberately low for a fast, robust test
    E_bd = np.where(is_ox, E_BD_TEST, 0.0)

    sim.set_permittivity(eps)
    sim.set_mobility(mu_n, mu_p)
    sim.set_doping(doping)
    sim.set_thermal_voltage(VT_300)
    sim.set_recombination(np.full(N, 1e-7), np.full(N, 1e-7))
    sim.set_effective_dos(np.full(N, 2.8e25), np.full(N, 1.04e25))
    sim.set_bandgap(np.full(N, 1.12))
    sim.set_electron_bc({0: 0.0, N - 1: 0.0})
    sim.set_hole_bc({0: 0.0, N - 1: 0.0})
    sim.set_dirichlet_potential({0: 0.0, N - 1: 0.0})

    oxide_ids = np.where(is_ox)[0]
    si_ids = np.where(~is_ox)[0]
    return sim, N, oxide_ids, si_ids, E_bd, is_ox


class TestDielectricBreakdown:
    """M7b dielectric breakdown: E_ox ~ Vg/tox, irreversible state flip."""

    def test_oxide_field_tracks_vg_over_tox(self):
        """The oxide |E| should scale ~ Vg/tox (parallel-plate capacitor).

        This validates the field that the breakdown detector consumes. With a
        modest gate bias the oxide field must be well below E_bd (no breakdown),
        establishing the sub-threshold baseline.
        """
        sim, N, oxide_ids, si_ids, E_bd, is_ox = _build_gate_oxide_stack()
        Vg = 1.0   # volts
        sim.set_dirichlet_potential({0: Vg, N - 1: 0.0})
        r = sim.solve()
        # |E| at oxide interior nodes.
        E_mag = np.sqrt(r["Ex"]**2 + r["Ey"]**2 + r["Ez"]**2)
        E_ox_max = float(np.max(E_mag[oxide_ids]))
        # Expect E_ox ~ Vg/tox within a factor of ~3 (discretisation + fringing).
        E_expected = Vg / 2e-9
        assert 0.2 * E_expected < E_ox_max < 5.0 * E_expected, (
            f"oxide field {E_ox_max:.3e} V/m not ~ Vg/tox={E_expected:.3e}")
        # At Vg=1V, tox=2nm -> E~5e8 V/m, right at the test E_bd; pick a lower
        # Vg to confirm the sub-threshold (no breakdown) case separately below.

    def test_breakdown_state_flips_above_ebd(self):
        """When the gate bias pushes |E_ox| above E_bd, the breakdown state
        must flip 0->1 at the stressed oxide nodes."""
        sim, N, oxide_ids, si_ids, E_bd, is_ox = _build_gate_oxide_stack()
        sim.set_breakdown_enabled(True)
        sim.set_breakdown_params(is_ox.astype(np.int8), E_bd, 1.0e-4)

        # Drive well past E_bd: Vg such that Vg/tox >> E_bd_test (5e8).
        # tox=2e-9 -> need Vg >> 1.0 V; use 3.0 V (E~1.5e9, 3x the threshold).
        Vg = 3.0
        sim.set_dirichlet_potential({0: Vg, N - 1: 0.0})
        sim.solve()
        bd = sim.breakdown_state()
        # At least one oxide node must have flipped to broken-down.
        assert bd[oxide_ids].max() == 1, (
            f"breakdown state did not flip at oxide nodes under Vg={Vg} "
            f"(E~{Vg/2e-9:.2e} >> E_bd={5e8:.2e}); detector broken")
        # Silicon nodes must NOT break down (E_bd=0 there -> never).
        assert bd[si_ids].max() == 0, "silicon node flagged broken (E_bd=0 guard broken)"

    def test_breakdown_is_irreversible(self):
        """Once a node breaks down, lowering the bias must NOT clear the state.

        This models the conductive filament: the breakdown persists. We drive
        past E_bd, confirm the flip, then drop to a low bias and confirm the
        state survives (the leakage term now applies on subsequent solves).
        """
        sim, N, oxide_ids, si_ids, E_bd, is_ox = _build_gate_oxide_stack()
        sim.set_breakdown_enabled(True)
        sim.set_breakdown_params(is_ox.astype(np.int8), E_bd, 1.0e-4)

        # 1. Drive past E_bd -> flip.
        sim.set_dirichlet_potential({0: 3.0, N - 1: 0.0})
        sim.solve()
        bd_after_stress = sim.breakdown_state().copy()
        n_broken = int(bd_after_stress[oxide_ids].sum())
        assert n_broken >= 1, "no breakdown induced in step 1"

        # 2. Drop to a low bias (well below threshold) on the SAME sim instance
        #    so bd_state_ persists.
        sim.set_dirichlet_potential({0: 0.1, N - 1: 0.0})
        sim.solve()
        bd_after_relax = sim.breakdown_state().copy()

        # The broken nodes must remain broken (irreversible).
        assert int(bd_after_relax[oxide_ids].sum()) >= n_broken, (
            "breakdown state cleared after lowering bias — irreversibility "
            "broken (the conductive filament should persist)")

    def test_no_breakdown_below_threshold(self):
        """At a gate bias where |E_ox| < E_bd everywhere, no node breaks down."""
        sim, N, oxide_ids, si_ids, E_bd, is_ox = _build_gate_oxide_stack()
        sim.set_breakdown_enabled(True)
        sim.set_breakdown_params(is_ox.astype(np.int8), E_bd, 1.0e-4)
        # Vg=0.5, tox=2e-9 -> E~2.5e8 < E_bd_test=5e8: sub-threshold.
        sim.set_dirichlet_potential({0: 0.5, N - 1: 0.0})
        sim.solve()
        bd = sim.breakdown_state()
        assert bd.max() == 0, (
            "breakdown triggered below threshold — detector too sensitive")
