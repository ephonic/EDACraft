"""Tests for tcad.geometry.shapes primitives."""

import numpy as np
import pytest

from tcad.geometry.shapes import Box, Sphere, Cylinder, Cone, Prism


class TestBox:
    def test_contains_single_point(self):
        box = Box(0, 1, 0, 1, 0, 1)
        assert box.contains(np.array([0.5]), np.array([0.5]), np.array([0.5]))[0]
        assert not box.contains(np.array([1.5]), np.array([0.5]), np.array([0.5]))[0]

    def test_contains_array(self):
        box = Box(-1, 1, -1, 1, -1, 1)
        x = np.array([-2, 0, 2])
        y = np.array([0, 0, 0])
        z = np.array([0, 0, 0])
        mask = box.contains(x, y, z)
        assert mask.tolist() == [False, True, False]

    def test_bbox(self):
        box = Box(1, 3, 2, 4, 0, 5)
        assert box.bbox() == ((1, 3), (2, 4), (0, 5))


class TestSphere:
    def test_contains_center(self):
        sp = Sphere(0, 0, 0, 2)
        assert sp.contains(np.array([0]), np.array([0]), np.array([0]))[0]

    def test_contains_surface(self):
        sp = Sphere(1, 1, 1, 1)
        # Point on surface (within radius)
        assert sp.contains(np.array([1]), np.array([1]), np.array([2]))[0]
        # Point outside
        assert not sp.contains(np.array([1]), np.array([1]), np.array([3]))[0]

    def test_bbox(self):
        sp = Sphere(1, 2, 3, 4)
        assert sp.bbox() == ((-3, 5), (-2, 6), (-1, 7))


class TestCylinder:
    def test_z_axis(self):
        cyl = Cylinder("z", 0, 0, 0, 10, 1)
        assert cyl.contains(np.array([0]), np.array([0]), np.array([5]))[0]
        assert not cyl.contains(np.array([2]), np.array([0]), np.array([5]))[0]
        assert not cyl.contains(np.array([0]), np.array([0]), np.array([11]))[0]

    def test_y_axis(self):
        cyl = Cylinder("y", 0, 0, 0, 10, 1)
        assert cyl.contains(np.array([0]), np.array([5]), np.array([0]))[0]

    def test_x_axis(self):
        cyl = Cylinder("x", 0, 0, 0, 10, 1)
        assert cyl.contains(np.array([5]), np.array([0]), np.array([0]))[0]

    def test_invalid_axis(self):
        cyl = Cylinder("w", 0, 0, 0, 10, 1)
        with pytest.raises(ValueError):
            cyl.contains(np.array([0]), np.array([0]), np.array([0]))


class TestCone:
    def test_contains_z_axis(self):
        cone = Cone("z", 0, 0, 0, 10, 0, 5)
        assert cone.contains(np.array([0]), np.array([0]), np.array([0]))[0]
        assert cone.contains(np.array([0]), np.array([0]), np.array([10]))[0]
        # At z=5, radius should be 2.5
        assert cone.contains(np.array([2]), np.array([0]), np.array([5]))[0]
        assert not cone.contains(np.array([3]), np.array([0]), np.array([5]))[0]

    def test_other_axis_not_implemented(self):
        cone = Cone("x", 0, 0, 0, 10, 0, 5)
        with pytest.raises(NotImplementedError):
            cone.contains(np.array([0]), np.array([0]), np.array([0]))


class TestPrism:
    def test_triangle_prism(self):
        vertices = np.array([[0, 0], [1, 0], [0.5, 1]])
        prism = Prism(vertices, 0, 10)
        assert prism.contains(np.array([0.5]), np.array([0.3]), np.array([5]))[0]
        assert not prism.contains(np.array([2]), np.array([0.3]), np.array([5]))[0]
        assert not prism.contains(np.array([0.5]), np.array([0.3]), np.array([15]))[0]

    def test_bbox(self):
        vertices = np.array([[0, 0], [2, 0], [1, 3]])
        prism = Prism(vertices, -1, 1)
        assert prism.bbox() == ((0.0, 2.0), (0.0, 3.0), (-1, 1))

    def test_path_cached(self):
        """Prism should cache matplotlib Path to avoid recreation."""
        vertices = np.array([[0, 0], [1, 0], [0.5, 1]])
        prism = Prism(vertices, 0, 1)
        assert hasattr(prism, "_path")
        # Multiple calls should reuse cached path
        r1 = prism.contains(np.array([0.5]), np.array([0.3]), np.array([0.5]))
        r2 = prism.contains(np.array([0.5]), np.array([0.3]), np.array([0.5]))
        assert r1[0] == r2[0]
