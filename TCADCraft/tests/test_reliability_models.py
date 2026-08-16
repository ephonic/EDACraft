"""Regression tests for dynamic reliability and emerging-material models."""

import numpy as np

from tcad.geometry.device_builder import Device, Region
from tcad.geometry.shapes import Box
from tcad.material.library import amorphous_igzo, wse2_channel
from tcad.mesh.structured_grid import StructuredGrid
from tcad.physics.reliability import CyclingDegradation, TrapKinetics
from tcad.simulator import Simulator


class TestTrapKinetics:
    def test_bias_drives_capture_and_release(self):
        model = TrapKinetics(
            density=1e24, trap_energy=0.0,
            capture_tau=1.0, emission_tau=1.0,
        )
        q_capture = model.advance(np.full(4, 0.5), 0.0, dt=5.0)
        assert np.all(model.occupancy > 0.99)
        assert np.all(q_capture < 0.0), "filled electron traps must be negative"
        q_release = model.advance(np.full(4, -0.5), 0.0, dt=5.0)
        assert np.all(model.occupancy < 0.01)
        assert np.all(q_release > 0.0)

    def test_exact_update_is_timestep_independent(self):
        one = TrapKinetics(1e23, capture_tau=2.0, emission_tau=3.0)
        many = TrapKinetics(1e23, capture_tau=2.0, emission_tau=3.0)
        one.advance(np.ones(3), 0.0, 4.0)
        for _ in range(40):
            many.advance(np.ones(3), 0.0, 0.1)
        assert np.allclose(one.occupancy, many.occupancy, rtol=1e-13, atol=1e-13)

    def test_field_accelerates_relaxation(self):
        slow = TrapKinetics(1e23, capture_tau=10.0, emission_tau=10.0,
                            field_acceleration=1e-4)
        fast = TrapKinetics(1e23, capture_tau=10.0, emission_tau=10.0,
                            field_acceleration=1e-4)
        slow.advance(np.ones(2), 0.0, 0.1)
        fast.advance(np.ones(2), 1e8, 0.1)
        assert np.mean(fast.occupancy) > np.mean(slow.occupancy)

    def test_poole_frenkel_barrier_lowering_uses_temperature_and_epsilon(self):
        base = TrapKinetics(
            1e23, capture_tau=10.0, emission_tau=10.0,
            poole_frenkel_epsilon_r=3.9,
        )
        hot = TrapKinetics(
            1e23, capture_tau=10.0, emission_tau=10.0,
            poole_frenkel_epsilon_r=3.9,
        )
        high_k = TrapKinetics(
            1e23, capture_tau=10.0, emission_tau=10.0,
            poole_frenkel_epsilon_r=20.0,
        )
        base.advance(np.ones(2), 1e8, 0.1, temperature=300.0)
        hot.advance(np.ones(2), 1e8, 0.1, temperature=400.0)
        high_k.advance(np.ones(2), 1e8, 0.1, temperature=300.0)
        assert np.mean(base.occupancy) > np.mean(hot.occupancy)
        assert np.mean(base.occupancy) > np.mean(high_k.occupancy)

    def test_capture_and_emission_use_distinct_time_scales(self):
        capture = TrapKinetics(1e23, capture_tau=0.1, emission_tau=100.0)
        emission = TrapKinetics(1e23, capture_tau=0.1, emission_tau=100.0)
        capture.advance(np.ones(2), 0.0, 0.1)
        emission.advance(-np.ones(2), 0.0, 0.1)
        capture_delta = np.mean(capture.occupancy) - 0.5
        emission_delta = 0.5 - np.mean(emission.occupancy)
        assert capture_delta > 100.0 * emission_delta


class TestCyclingDegradation:
    def test_wakeup_then_fatigue(self):
        model = CyclingDegradation(
            wakeup_cycles=10.0, fatigue_cycles=200.0,
            wakeup_gain=0.2, fatigue_loss=0.9,
            reference_field=1.0, field_exponent=1.0,
        )
        early = [model.advance(1.0, 1.0) for _ in range(10)]
        peak = max(early)
        for _ in range(1000):
            late = model.advance(1.0, 1.0)
        assert peak > early[0], "wake-up state must initially activate domains"
        assert late < peak, "fatigue must dominate at long cycle count"
        assert 0.0 <= model.wakeup_state <= 1.0
        assert 0.0 <= model.fatigue_state <= 1.0


class _CoreRecorder:
    def __init__(self):
        self.phi_bc = None
        self.n_bc = None
        self.p_bc = None
        self.mu_n = None
        self.Nc = None

    def set_dirichlet_potential(self, value):
        self.phi_bc = value

    def set_electron_bc(self, value):
        self.n_bc = value

    def set_hole_bc(self, value):
        self.p_bc = value

    def set_mobility(self, mu_n, _mu_p):
        self.mu_n = np.asarray(mu_n)

    def set_effective_dos(self, Nc, _Nv):
        self.Nc = np.asarray(Nc)


def _material_grid(material):
    dev = Device("material-test")
    dev.add_region(Region("channel", Box(0, 10e-9, 0, 1e-9, 0, 1e-9), material))
    grid = StructuredGrid(dev.bbox(), 3, 1, 1)
    for name, values in grid.create_device_fields(dev).items():
        grid.add_field(name, values)
    grid.add_field("contact_source", np.array([1, 0, 0], dtype=np.int8))
    return grid


class TestEmergingMaterials:
    def test_igzo_metadata_drives_tail_dos_and_pbti_factory(self):
        grid = _material_grid(amorphous_igzo())
        sim = Simulator(grid)
        recorder = _CoreRecorder()
        sim._sim = recorder
        sim.set_disordered_transport(True)
        base_Nc = grid.fields["Nc"] * 1e6
        assert np.all(recorder.Nc > base_Nc)
        pbti = sim.create_pbti_trap_model()
        assert pbti.density > 0.0
        assert np.all(pbti.mask)

    def test_wse2_workfunction_sets_ambipolar_schottky_population(self):
        grid = _material_grid(wse2_channel())
        sim = Simulator(grid)
        recorder = _CoreRecorder()
        sim._sim = recorder
        sim.set_contact("source", 0.0, workfunction=4.6)
        n_high_wf = recorder.n_bc[0]
        p_high_wf = recorder.p_bc[0]
        sim.set_contact("source", 0.0, workfunction=4.0)
        n_low_wf = recorder.n_bc[0]
        p_low_wf = recorder.p_bc[0]
        assert n_low_wf > n_high_wf, "lower metal workfunction should lower electron barrier"
        assert p_high_wf > p_low_wf, "higher metal workfunction should lower hole barrier"

    def test_igzo_and_wse2_templates_preserve_specialized_metadata(self):
        igzo = Device.igzo_tft(Lg=100e-9, Lsd=20e-9, W=10e-9,
                               t_ch=5e-9, tox=5e-9)
        igzo_grid = StructuredGrid(igzo.bbox(), 8, 2, 4)
        igzo_fields = igzo_grid.create_device_fields(igzo)
        assert np.max(igzo_fields["tail_DOS"]) > 0.0
        assert np.max(igzo_fields["pbti_Nt"]) > 0.0

        wse2 = Device.wse2_schottky_fet(
            Lg=40e-9, Lsd=10e-9, W=5e-9, t_ch=2e-9, tox=3e-9,
            source_workfunction=4.3, drain_workfunction=4.7,
        )
        assert wse2.contact_workfunctions == {"source": 4.3, "drain": 4.7}
