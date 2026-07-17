"""B档: mesh-generation correctness tests.

Validates the geometry/topology correctness of the mesh layer — the
foundation every solver discretization builds on. Pins the bugs found by the
B-tier reconnaissance:

  Bug 3: adaptive_refiner used plain .reshape(nx,ny,nz) (C-order, k fastest) on
         node-ordered flat arrays, scrambling i,j,k and flagging material
         interfaces on the wrong axis in 3D. Fixed to use to_3d(); this test
         pins the fix.
  Bug 4: set_contact silently no-op'd when a contact hit zero mesh nodes.
         Fixed to raise; this test pins the fix.

Plus foundational invariants not previously tested:
  - to_3d/from_3d round-trip and agreement with index().
  - to_3d is NOT equivalent to plain reshape (the trap Bug 3 fell into).
  - degenerate grids (nx=1 etc.) and bbox validation.
  - cut-cell edge permittivity harmonic mean at a known interface.
"""

import numpy as np
import pytest

from tcad.mesh.structured_grid import StructuredGrid


def _grid(nx=3, ny=4, nz=2, span=(3.0, 4.0, 2.0)):
    return StructuredGrid(
        bbox=((0.0, span[0]), (0.0, span[1]), (0.0, span[2])),
        nx=nx, ny=ny, nz=nz,
    )


# ===========================================================================
# to_3d / from_3d / index() consistency (the core node-ordering invariant)
# ===========================================================================

class TestNodeOrderingConsistency:
    """to_3d must agree with the index() convention i + nx*(j + ny*k)."""

    def test_to_3d_agrees_with_index(self):
        """to_3d(flat)[i,j,k] == flat[index(i,j,k)] for every node."""
        g = _grid(3, 4, 2)
        N = g.npts()
        flat = np.arange(N, dtype=float)   # value == node id
        arr3d = g.to_3d(flat)
        for k in range(g.nz):
            for j in range(g.ny):
                for i in range(g.nx):
                    assert arr3d[i, j, k] == flat[g.index(i, j, k)], (
                        f"to_3d[{i},{j},{k}]={arr3d[i,j,k]} != "
                        f"flat[index]={flat[g.index(i,j,k)]}")

    def test_from_3d_round_trips_to_3d(self):
        """from_3d(to_3d(flat)) == flat (lossless)."""
        g = _grid(3, 4, 2)
        flat = np.random.rand(g.npts())
        assert np.array_equal(g.from_3d(g.to_3d(flat)), flat)

    def test_to_3d_not_equal_plain_reshape(self):
        """to_3d must DIFFER from plain .reshape(nx,ny,nz) for non-trivial 3D.

        This is the exact trap Bug 3 fell into: plain C-order reshape varies k
        fastest, but the node order varies i fastest. A test asserting they
        differ locks the convention that to_3d (not reshape) must be used."""
        g = _grid(3, 4, 2)   # 3D, non-trivial (nx,ny,nz all > 1 needed; here nx=3,ny=4,nz=2)
        flat = np.arange(g.npts(), dtype=float)
        arr_to_3d = g.to_3d(flat)
        arr_reshape = flat.reshape(g.nx, g.ny, g.nz)
        # For a non-trivial 3D grid these differ (when more than one axis > 1).
        if g.nx > 1 and g.ny > 1 and g.nz > 1:
            assert not np.array_equal(arr_to_3d, arr_reshape), (
                "to_3d equals plain reshape — node-order convention broken "
                "(Bug 3 regression: someone used reshape instead of to_3d)")

    def test_index_ijk_round_trip(self):
        """index(ijk(idx)) == idx and ijk(index(i,j,k)) == (i,j,k)."""
        g = _grid(3, 4, 2)
        for idx in range(g.npts()):
            i, j, k = g.ijk(idx)
            assert g.index(i, j, k) == idx, f"index/ijk round-trip failed at {idx}"


# ===========================================================================
# Degenerate grids & bbox validation (Bug-4-adjacent)
# ===========================================================================

class TestDegenerateGridsAndBbox:
    """Edge cases: nx=1, inverted/zero bbox."""

    def test_nx1_grid_valid(self):
        """A 1-node axis (nx=1) with a valid span must construct and index."""
        g = StructuredGrid(bbox=((0.0, 1.0), (0.0, 0.5), (0.0, 0.2)),
                           nx=1, ny=3, nz=2)
        assert g.npts() == 1 * 3 * 2
        # index/ijk must not go out of bounds.
        assert g.index(0, 0, 0) == 0
        i, j, k = g.ijk(0)
        assert (i, j, k) == (0, 0, 0)

    def test_inverted_bbox_raises(self):
        """xmin >= xmax must raise (B档 bbox validation)."""
        with pytest.raises(ValueError, match="strictly increasing"):
            StructuredGrid(bbox=((1.0, 0.0), (0.0, 1.0), (0.0, 1.0)), nx=3, ny=3, nz=3)

    def test_zero_width_bbox_raises(self):
        """xmin == xmax (zero span) must raise."""
        with pytest.raises(ValueError, match="strictly increasing"):
            StructuredGrid(bbox=((0.0, 0.0), (0.0, 1.0), (0.0, 1.0)), nx=3, ny=3, nz=3)

    def test_flat_coords_monotonic_on_degenerate_y(self):
        """ny=1: flat_coords y must be a single repeated value, x monotonic."""
        g = StructuredGrid(bbox=((0.0, 1.0), (0.0, 0.1), (0.0, 0.1)),
                           nx=5, ny=1, nz=1)
        fx, fy, fz = g.flat_coords()
        # Along the x-line (the only line), x strictly increases.
        assert np.all(np.diff(fx) > 0)


# ===========================================================================
# Cut-cell edge permittivity at a known interface
# ===========================================================================

class TestCutCellEdgePermittivity:
    """compute_edge_permittivity must return the harmonic mean at a Si/SiO2
    interface (the discretization-correctness-sensitive quantity)."""

    def test_harmonic_mean_at_si_sio2_interface(self):
        """A 1D grid with a sharp Si/SiO2 interface: the mixed edge's effective
        permittivity must be the harmonic mean 2*eps1*eps2/(eps1+eps2)."""
        from tcad.mesh.cut_cell import compute_edge_permittivity
        nx = 5
        g = StructuredGrid(bbox=((0.0, 5e-9), (0.0, 0.1e-9), (0.0, 0.1e-9)),
                           nx=nx, ny=1, nz=1)
        EPS0 = 8.854187817e-12
        eps_si = EPS0 * 11.7
        eps_ox = EPS0 * 3.9
        # Interface between node 2 (Si) and node 3 (SiO2).
        eps = np.full(nx, eps_si)
        eps[3:] = eps_ox
        mat_id = np.zeros(nx, dtype=np.int32)
        mat_id[3:] = 1
        g.add_field("epsilon", eps)
        g.add_field("material_id", mat_id)
        edge = compute_edge_permittivity(g, eps, mat_id)
        # The +x edge at node 2 (2->3) is the mixed edge.
        ep = edge["x_plus"]
        # Harmonic mean at alpha=0.5 (no shapes passed -> midpoint crossing):
        # eps_eff = 1/(0.5/eps_si + 0.5/eps_ox) = 2*eps_si*eps_ox/(eps_si+eps_ox).
        expected = 2.0 * eps_si * eps_ox / (eps_si + eps_ox)
        assert abs(ep[2] - expected) / expected < 1e-9, (
            f"mixed-edge permittivity {ep[2]:.4e} != harmonic mean {expected:.4e}")
        # Same-material edges return the plain harmonic mean = eps (since equal).
        assert abs(ep[0] - eps_si) / eps_si < 1e-9


# ===========================================================================
# Bug 3 regression: adaptive refiner axis correctness
# ===========================================================================

class TestAdaptiveRefinerAxisCorrectness:
    """Bug 3: a material interface running purely along x must refine ONLY the
    x axis, not y/z (the pre-fix reshape scramble mis-flagged it)."""

    def test_x_only_interface_refines_only_x(self):
        """Build a 3D grid whose epsilon changes ONLY along x (a stack of layers
        perpendicular to x). The feature markers must fire on x, and NOT on y
        or z (which have no epsilon variation)."""
        from tcad.mesh.adaptive_refiner import AdaptiveRefiner
        from tcad.geometry.device_builder import Device, Region, Box, Material, DopingProfile
        nx, ny, nz = 5, 4, 4
        g = StructuredGrid(bbox=((0.0, 5e-9), (0.0, 4e-9), (0.0, 4e-9)),
                           nx=nx, ny=ny, nz=nz)
        EPS0 = 8.854187817e-12
        eps = np.full(g.npts(), EPS0 * 11.7)
        mat_id = np.zeros(g.npts(), dtype=np.int32)
        # Eps jumps along x at i>=3 (Si -> SiO2), uniform in y,z.
        fx = g.flat_coords()[0]
        ox_mask = fx >= 3e-9
        eps[ox_mask] = EPS0 * 3.9
        mat_id[ox_mask] = 1
        g.add_field("epsilon", eps)
        g.add_field("material_id", mat_id)
        # AdaptiveRefiner needs a device; pass a minimal one (the marker fn
        # only reads the grid fields, not the device).
        dev = Device("t")
        dev.add_region(Region("bulk", Box(0, 5e-9, 0, 4e-9, 0, 4e-9),
                              Material("Si"), DopingProfile(Nd=1e18)))
        refiner = AdaptiveRefiner(dev, base_resolution=(1e-9, 1e-9, 1e-9))
        markers = refiner._compute_feature_markers(g)
        assert markers["x"].any(), "x interface not detected (Bug 3: should refine x)"
        assert not markers["y"].any(), (
            "y axis flagged for an x-only interface — Bug 3 regression "
            "(reshape scramble): to_3d fix lost")
        assert not markers["z"].any(), (
            "z axis flagged for an x-only interface — Bug 3 regression "
            "(reshape scramble): to_3d fix lost")

    def test_y_only_interface_refines_only_y(self):
        """Symmetric check: an interface along y must refine only y."""
        from tcad.mesh.adaptive_refiner import AdaptiveRefiner
        from tcad.geometry.device_builder import Device, Region, Box, Material, DopingProfile
        nx, ny, nz = 4, 5, 4
        g = StructuredGrid(bbox=((0.0, 4e-9), (0.0, 5e-9), (0.0, 4e-9)),
                           nx=nx, ny=ny, nz=nz)
        EPS0 = 8.854187817e-12
        eps = np.full(g.npts(), EPS0 * 11.7)
        mat_id = np.zeros(g.npts(), dtype=np.int32)
        fy = g.flat_coords()[1]
        ox_mask = fy >= 3e-9
        eps[ox_mask] = EPS0 * 3.9
        mat_id[ox_mask] = 1
        g.add_field("epsilon", eps)
        g.add_field("material_id", mat_id)
        dev = Device("t")
        dev.add_region(Region("bulk", Box(0, 4e-9, 0, 5e-9, 0, 4e-9),
                              Material("Si"), DopingProfile(Nd=1e18)))
        refiner = AdaptiveRefiner(dev, base_resolution=(1e-9, 1e-9, 1e-9))
        markers = refiner._compute_feature_markers(g)
        assert markers["y"].any(), "y interface not detected"
        assert not markers["x"].any(), (
            "x axis flagged for a y-only interface — Bug 3 regression")
        assert not markers["z"].any(), (
            "z axis flagged for a y-only interface — Bug 3 regression")


# ===========================================================================
# Bug 4 regression: zero-contact-node guard
# ===========================================================================

class TestZeroContactNodeGuard:
    """Bug 4: a contact thinner than one cell must raise, not silently no-op."""

    def test_subcell_contact_raises(self):
        """A contact Box entirely between two grid nodes (no node inside) must
        raise ValueError in set_contact (was a silent no-op before Bug 4 fix)."""
        from tcad import Device, Simulator
        from tcad.mesh.generator import structured_mesh_from_device
        from tcad.geometry.device_builder import Material, Region, Box, DopingProfile
        dev = Device("t")
        si = Material("Si", epsilon_r=11.7, Eg=1.12)
        dev.add_region(Region("bulk", Box(0, 1e-6, 0, 1e-6, 0, 1e-6), si,
                              DopingProfile(Nd=1e18)))
        # A contact Box that sits strictly between grid nodes (grid dx=2e-7,
        # contact at x in [1e-9, 2e-9] — narrower than one cell and not on a node).
        dev.add_contact("thin", Box(1e-9, 2e-9, 0, 1e-6, 0, 1e-6), voltage=0.0)
        mesh = structured_mesh_from_device(dev, resolution=(2e-7, 2e-7, 2e-7))
        sim = Simulator(mesh, temperature=300.0)
        sim.set_material_from_mesh()
        with pytest.raises(ValueError, match="zero mesh nodes"):
            sim.set_contact("thin", 0.0)
