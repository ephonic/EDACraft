"""Tests for tcad.mesh.adaptive_refiner."""

import numpy as np
import pytest

from tcad.mesh.adaptive_refiner import AdaptiveRefiner
from tcad.mesh.structured_grid import StructuredGrid
from tcad.geometry.device_builder import Device, Region, Material, DopingProfile, Box


class TestAdaptiveRefiner:
    def test_basic_refinement(self):
        dev = Device.pnjunction()
        refiner = AdaptiveRefiner(dev, base_resolution=(0.5e-6, 0.5e-6, 0.5e-6))
        fine = refiner.generate_feature_refined_mesh(level=1)
        assert isinstance(fine, StructuredGrid)
        assert fine.nx >= 3
        assert fine.ny >= 3
        assert fine.nz >= 3
        assert "doping" in fine.fields

    def test_refinement_increases_resolution(self):
        dev = Device.pnjunction()
        refiner = AdaptiveRefiner(dev, base_resolution=(0.5e-6, 0.5e-6, 0.5e-6))
        coarse = refiner.generate_feature_refined_mesh(level=0)
        fine = refiner.generate_feature_refined_mesh(level=1)
        # Level 1 should have at least as many nodes as level 0
        assert fine.npts() >= coarse.npts()

    def test_max_level_clamping(self):
        dev = Device.pnjunction()
        refiner = AdaptiveRefiner(dev, base_resolution=(0.5e-6, 0.5e-6, 0.5e-6), max_level=1)
        fine = refiner.generate_feature_refined_mesh(level=10)
        # Should be clamped to ratio^max_level, not ratio^level
        # Just verify it doesn't explode
        assert fine.npts() < 1e7  # sanity bound

    def test_feature_markers_doping(self):
        """High doping gradient should trigger markers."""
        dev = Device()
        si = Material("Silicon")
        # Abrupt junction: p+ next to n+
        dev.add_region(Region("p", Box(0, 1, 0, 1, 0, 1), si, DopingProfile(Na=1e21)))
        dev.add_region(Region("n", Box(1, 2, 0, 1, 0, 1), si, DopingProfile(Nd=1e21)))
        refiner = AdaptiveRefiner(dev, base_resolution=(0.5, 0.5, 0.5))
        coarse = refiner.generate_feature_refined_mesh(level=0)
        markers = refiner._compute_feature_markers(coarse)
        # There should be at least one marked cell near the junction
        assert sum(m.sum() for m in markers.values()) > 0

    def test_feature_markers_epsilon(self):
        """Material interface should trigger markers."""
        dev = Device()
        si = Material("Silicon", epsilon_r=11.7)
        ox = Material("Oxide", epsilon_r=3.9)
        dev.add_region(Region("si", Box(0, 2, 0, 1, 0, 1), si))
        dev.add_region(Region("ox", Box(0, 1, 0, 1, 0, 1), ox))
        refiner = AdaptiveRefiner(dev, base_resolution=(0.5, 0.5, 0.5))
        coarse = refiner.generate_feature_refined_mesh(level=0)
        markers = refiner._compute_feature_markers(coarse)
        # Interface should be marked
        assert sum(m.sum() for m in markers.values()) > 0

    def test_prolongate(self):
        dev = Device.pnjunction()
        refiner = AdaptiveRefiner(dev, base_resolution=(0.5e-6, 0.5e-6, 0.5e-6))
        coarse = refiner.generate_feature_refined_mesh(level=0)
        fine = refiner.generate_feature_refined_mesh(level=1)
        coarse.add_field("phi", np.ones(coarse.npts()))
        prolonged = AdaptiveRefiner.prolongate(coarse, fine, "phi")
        assert prolonged.shape == (fine.npts(),)
        np.testing.assert_array_almost_equal(prolonged, np.ones(fine.npts()))

    def test_restrict(self):
        dev = Device.pnjunction()
        refiner = AdaptiveRefiner(dev, base_resolution=(0.5e-6, 0.5e-6, 0.5e-6))
        coarse = refiner.generate_feature_refined_mesh(level=0)
        fine = refiner.generate_feature_refined_mesh(level=1)
        fine.add_field("phi", np.ones(fine.npts()))
        restricted = AdaptiveRefiner.restrict(fine, coarse, "phi")
        assert restricted.shape == (coarse.npts(),)
        np.testing.assert_array_almost_equal(restricted, np.ones(coarse.npts()))

    def test_prolongate_missing_field(self):
        dev = Device.pnjunction()
        refiner = AdaptiveRefiner(dev, base_resolution=(0.5e-6, 0.5e-6, 0.5e-6))
        coarse = refiner.generate_feature_refined_mesh(level=0)
        fine = refiner.generate_feature_refined_mesh(level=1)
        with pytest.raises(KeyError):
            AdaptiveRefiner.prolongate(coarse, fine, "missing")
    def test_anisotropic_refinement_preset_gaa(self):
        """GAA preset should limit x-refinement while allowing y/z to refine more."""
        dev = Device.gaa()
        base = (5e-9, 5e-9, 5e-9)
        refiner = AdaptiveRefiner(dev, base_resolution=base, max_level=3)
        mesh_preset = refiner.generate_feature_refined_mesh(level=3, preset="gaa")

        refiner2 = AdaptiveRefiner(dev, base_resolution=base, max_level=3)
        mesh_uniform = refiner2.generate_feature_refined_mesh(level=3)

        px, py, pz = mesh_preset.shape()
        ux, uy, uz = mesh_uniform.shape()
        # GAA preset limits x more than uniform; y/z may be similar or smaller
        assert px <= ux, f"GAA x should be <= uniform: {px} vs {ux}"
        # Both should have refined relative to a level-0 mesh
        coarse = AdaptiveRefiner(dev, base_resolution=base, max_level=3).generate_feature_refined_mesh(level=0)
        cx, cy, cz = coarse.shape()
        assert px > cx and pz > cz

    def test_anisotropic_refinement_manual_axes(self):
        """Manual axis_refinement should control per-axis resolution."""
        dev = Device.gaa()
        base = (5e-9, 5e-9, 5e-9)
        refiner = AdaptiveRefiner(
            dev, base_resolution=base, max_level=3,
            axis_refinement={"x": 4, "y": 1, "z": 1}
        )
        mesh = refiner.generate_feature_refined_mesh(level=3)
        mx, my, mz = mesh.shape()

        refiner_uniform = AdaptiveRefiner(dev, base_resolution=base, max_level=3)
        mesh_uniform = refiner_uniform.generate_feature_refined_mesh(level=3)
        ux, uy, uz = mesh_uniform.shape()

        # x allowed to refine up to 4x, y/z clamped to 1x (no refinement)
        assert mx >= ux * 0.8, f"x should refine: {mx} vs {ux}"
        assert my <= uy, f"y should not refine more than uniform: {my} vs {uy}"
        assert mz <= uz, f"z should not refine more than uniform: {mz} vs {uz}"

    def test_directional_thresholds(self):
        """Lower directional threshold should trigger more markers in that axis."""
        dev = Device.gaa()
        base = (5e-9, 5e-9, 5e-9)
        refiner_high = AdaptiveRefiner(
            dev, base_resolution=base, max_level=3,
            directional_thresholds={"x": 1e25, "y": 1e25, "z": 1e25}
        )
        markers_high = refiner_high._compute_feature_markers(
            refiner_high.generate_feature_refined_mesh(level=0)
        )

        refiner_low = AdaptiveRefiner(
            dev, base_resolution=base, max_level=3,
            directional_thresholds={"x": 1e10, "y": 1e10, "z": 1e10}
        )
        markers_low = refiner_low._compute_feature_markers(
            refiner_low.generate_feature_refined_mesh(level=0)
        )

        # Lower threshold -> more markers
        assert markers_low["x"].sum() >= markers_high["x"].sum()
        assert markers_low["y"].sum() >= markers_high["y"].sum()
        assert markers_low["z"].sum() >= markers_high["z"].sum()

    def test_preset_unknown_raises(self):
        """Unknown preset should raise ValueError."""
        dev = Device.mosfet()
        refiner = AdaptiveRefiner(dev, base_resolution=(20e-9, 20e-9, 20e-9))
        with pytest.raises(ValueError):
            refiner.generate_feature_refined_mesh(level=1, preset="unknown")


class TestSolutionDrivenRefinement:
    def test_solution_error_markers_gradient(self):
        """Solution error markers should flag cells with large phi gradients."""
        dev = Device.pnjunction()
        refiner = AdaptiveRefiner(dev, base_resolution=(0.5e-6, 0.5e-6, 0.5e-6))
        coarse = refiner.generate_feature_refined_mesh(level=1)

        # Fake results with a strong gradient in x
        npts = coarse.npts()
        x = np.linspace(0, 1, coarse.nx)
        phi = np.zeros(npts)
        for k in range(coarse.nz):
            for j in range(coarse.ny):
                for i in range(coarse.nx):
                    idx = i + coarse.nx * (j + coarse.ny * k)
                    phi[idx] = x[i] ** 2  # quadratic -> large gradient

        results = {"phi": phi, "n": np.zeros(npts), "p": np.zeros(npts)}
        markers = refiner._compute_solution_error_markers(coarse, results, level=0, mode="gradient")
        # Cells with large gradient should be marked
        assert sum(m.sum() for m in markers.values()) > 0

    def test_solution_error_markers_residual(self):
        """Residual mode should flag cells with large Laplacian."""
        dev = Device.pnjunction()
        refiner = AdaptiveRefiner(dev, base_resolution=(0.5e-6, 0.5e-6, 0.5e-6))
        coarse = refiner.generate_feature_refined_mesh(level=1)

        npts = coarse.npts()
        x = np.linspace(0, 1, coarse.nx)
        phi = np.zeros(npts)
        for k in range(coarse.nz):
            for j in range(coarse.ny):
                for i in range(coarse.nx):
                    idx = i + coarse.nx * (j + coarse.ny * k)
                    phi[idx] = x[i] ** 3  # cubic -> non-zero Laplacian

        results = {"phi": phi}
        markers = refiner._compute_solution_error_markers(coarse, results, level=0, mode="residual")
        assert sum(m.sum() for m in markers.values()) > 0

    def test_solution_error_markers_tightens_with_level(self):
        """Higher level should produce fewer markers (tighter thresholds)."""
        dev = Device.pnjunction()
        refiner = AdaptiveRefiner(dev, base_resolution=(0.5e-6, 0.5e-6, 0.5e-6))
        coarse = refiner.generate_feature_refined_mesh(level=1)

        npts = coarse.npts()
        results = {"phi": np.random.rand(npts), "n": np.random.rand(npts), "p": np.random.rand(npts)}

        markers_l0 = refiner._compute_solution_error_markers(coarse, results, level=0)
        markers_l2 = refiner._compute_solution_error_markers(coarse, results, level=2)

        total_l0 = sum(m.sum() for m in markers_l0.values())
        total_l2 = sum(m.sum() for m in markers_l2.values())
        assert total_l2 <= total_l0, "Higher level should produce fewer or equal markers"

    def test_refine_from_solution_increases_nodes(self):
        """refine_from_solution should produce a finer mesh."""
        dev = Device.pnjunction()
        refiner = AdaptiveRefiner(dev, base_resolution=(0.5e-6, 0.5e-6, 0.5e-6))
        coarse = refiner.generate_feature_refined_mesh(level=1)

        npts = coarse.npts()
        results = {"phi": np.random.rand(npts), "n": np.random.rand(npts), "p": np.random.rand(npts)}
        fine = refiner.refine_from_solution(coarse, results, level=1)

        assert fine.npts() >= coarse.npts()

    def test_refine_from_solution_combine_intersection(self):
        """Intersection combine mode should produce fewer refined cells."""
        dev = Device.pnjunction()
        refiner = AdaptiveRefiner(dev, base_resolution=(0.5e-6, 0.5e-6, 0.5e-6))
        coarse = refiner.generate_feature_refined_mesh(level=1)

        npts = coarse.npts()
        results = {"phi": np.random.rand(npts), "n": np.random.rand(npts), "p": np.random.rand(npts)}

        fine_union = refiner.refine_from_solution(coarse, results, level=1, combine="union")
        fine_inter = refiner.refine_from_solution(coarse, results, level=1, combine="intersection")

        # Intersection should produce <= nodes than union
        assert fine_inter.npts() <= fine_union.npts()


class TestAdaptiveLoop:
    def test_adaptive_solve_runs(self):
        """run_adaptive_solve should complete without errors and return history."""
        dev = Device.pnjunction()
        refiner = AdaptiveRefiner(dev, base_resolution=(1e-6, 1e-6, 1e-6))

        # Create a minimal simulator
        coarse = refiner.generate_feature_refined_mesh(level=1)
        from tcad.simulator import Simulator
        sim = Simulator(coarse, temperature=300.0)
        sim.set_material_from_mesh()
        for name in dev.contacts:
            _, voltage = dev.contacts[name]
            sim.set_contact(name, float(voltage))

        grids, results, history = refiner.run_adaptive_solve(
            sim, max_rounds=2, initial_level=1, refine_level=1, verbose=False,
            sim_kwargs={"max_iter": 100, "tol": 1e-8}
        )

        assert len(grids) >= 1
        assert len(results) >= 1
        assert "npts" in history
        assert "max_error" in history
        # Each round should have increasing mesh size (or same)
        for i in range(1, len(history["npts"])):
            assert history["npts"][i] >= history["npts"][i - 1]

    def test_adaptive_solve_convergence(self):
        """Adaptive loop should refine mesh and complete all rounds or converge early."""
        dev = Device.pnjunction()
        refiner = AdaptiveRefiner(dev, base_resolution=(1e-6, 1e-6, 1e-6))

        coarse = refiner.generate_feature_refined_mesh(level=1)
        from tcad.simulator import Simulator
        sim = Simulator(coarse, temperature=300.0)
        sim.set_material_from_mesh()
        for name in dev.contacts:
            _, voltage = dev.contacts[name]
            sim.set_contact(name, float(voltage))

        grids, results, history = refiner.run_adaptive_solve(
            sim, max_rounds=3, initial_level=1, refine_level=1,
            tol=1e-4, verbose=False,
            sim_kwargs={"max_iter": 100, "tol": 1e-8}
        )

        # At least one round should have run
        assert len(grids) >= 1
        # Mesh size should increase (or stay same) across rounds
        for i in range(1, len(history["npts"])):
            assert history["npts"][i] >= history["npts"][i - 1]
        # Final mesh should be larger than initial
        if len(grids) > 1:
            assert grids[-1].npts() > grids[0].npts()

